"""
Training Script for Fine-Tuning SlowFast-R101 on Custom Data
Pretrained on Kinetics-400, fine-tuned for binary: Normal vs Suspicious activity.
Designed for Kaggle T4 x2 GPU environment.

Usage:
    python train_model.py --data_dir /path/to/dataset --epochs 30 --batch_size 4

Dataset structure expected:
    dataset/
    ├── train/
    │   ├── normal/
    │   │   ├── video_001/
    │   │   │   ├── frame_001.jpg
    │   │   │   ├── frame_002.jpg
    │   │   │   └── ...
    │   │   └── video_002/
    │   └── suspicious/
    │       ├── video_001/
    │       └── ...
    └── val/
        ├── normal/
        └── suspicious/
"""
import argparse
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torch.cuda.amp import GradScaler, autocast

# Add pytorchvideo to path for model loading
PYTORCHVIDEO_DIR = str(Path(__file__).parent.parent / 'pytorchvideo-main')
sys.path.insert(0, PYTORCHVIDEO_DIR)


class VideoFrameDataset(Dataset):
    """
    Dataset that loads 32-frame clips from directories of extracted frames.

    Each video is a directory of sequential frame images.
    Labels are determined by parent directory name (normal/suspicious).
    Returns frames as a list of two tensors (slow and fast pathways).
    """

    SLOWFAST_ALPHA = 4  # temporal stride between slow and fast pathways

    def __init__(self, root_dir, num_frames=32, transform=None):
        self.root_dir = Path(root_dir)
        self.num_frames = num_frames
        self.transform = transform or transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(256),
            transforms.CenterCrop(256),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.45, 0.45, 0.45],
                std=[0.225, 0.225, 0.225]
            ),
        ])

        self.samples = []
        self.labels = {'normal': 0, 'suspicious': 1}

        for label_name, label_idx in self.labels.items():
            label_dir = self.root_dir / label_name
            if not label_dir.exists():
                print(f"Warning: Directory not found: {label_dir}")
                continue

            for video_dir in sorted(label_dir.iterdir()):
                if video_dir.is_dir():
                    frames = sorted([
                        f for f in video_dir.iterdir()
                        if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.bmp')
                    ])
                    if len(frames) >= self.num_frames:
                        self.samples.append({
                            'frames': frames,
                            'label': label_idx,
                            'video_name': video_dir.name,
                        })

        print(f"Loaded {len(self.samples)} video clips from {root_dir}")
        for label_name, label_idx in self.labels.items():
            count = sum(1 for s in self.samples if s['label'] == label_idx)
            print(f"  {label_name}: {count} clips")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        frames_paths = sample['frames']
        label = sample['label']

        # Sample num_frames evenly from the video
        total = len(frames_paths)
        indices = np.linspace(0, total - 1, self.num_frames, dtype=int)

        frames = []
        for i in indices:
            img = cv2.imread(str(frames_paths[i]))
            if img is None:
                img = np.zeros((224, 224, 3), dtype=np.uint8)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            if self.transform:
                img = self.transform(img)
            frames.append(img)

        # Stack: (32, 3, 256, 256) -> permute to (3, 32, 256, 256)
        video_tensor = torch.stack(frames, dim=0)  # (32, 3, 256, 256)
        video_tensor = video_tensor.permute(1, 0, 2, 3)  # (3, 32, 256, 256)

        # PackPathway: split into slow and fast pathways
        slow_pathway = video_tensor[:, ::self.SLOWFAST_ALPHA, :, :]  # (3, 8, 256, 256)
        fast_pathway = video_tensor  # (3, 32, 256, 256)

        return [slow_pathway, fast_pathway], label


def collate_slowfast(batch):
    """Custom collate for SlowFast dual-pathway inputs."""
    slow_list, fast_list, labels = [], [], []
    for pathways, label in batch:
        slow_list.append(pathways[0])
        fast_list.append(pathways[1])
        labels.append(label)
    slow = torch.stack(slow_list)
    fast = torch.stack(fast_list)
    labels = torch.tensor(labels, dtype=torch.long)
    return [slow, fast], labels


def train_one_epoch(model, dataloader, criterion, optimizer, scaler, device, epoch):
    """Train for one epoch with mixed precision."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for batch_idx, (pathways, labels) in enumerate(dataloader):
        slow = pathways[0].to(device)
        fast = pathways[1].to(device)
        labels = labels.to(device)

        optimizer.zero_grad()

        with autocast():
            outputs = model([slow, fast])
            loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

        if (batch_idx + 1) % 10 == 0:
            acc = 100. * correct / total
            avg_loss = running_loss / (batch_idx + 1)
            print(f"  Epoch {epoch} | Batch {batch_idx+1}/{len(dataloader)} | "
                  f"Loss: {avg_loss:.4f} | Acc: {acc:.2f}%")

    epoch_loss = running_loss / len(dataloader)
    epoch_acc = 100. * correct / total
    return epoch_loss, epoch_acc


def validate(model, dataloader, criterion, device):
    """Validate the model."""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for pathways, labels in dataloader:
            slow = pathways[0].to(device)
            fast = pathways[1].to(device)
            labels = labels.to(device)

            outputs = model([slow, fast])
            loss = criterion(outputs, labels)

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

    val_loss = running_loss / len(dataloader)
    val_acc = 100. * correct / total
    return val_loss, val_acc


def main():
    parser = argparse.ArgumentParser(description='Fine-tune SlowFast-R101 for Activity Classification')
    parser.add_argument('--data_dir', type=str, required=True, help='Path to dataset directory')
    parser.add_argument('--output_dir', type=str, default='./trained_models', help='Output directory for saved models')
    parser.add_argument('--epochs', type=int, default=30, help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=4, help='Batch size (SlowFast needs more memory)')
    parser.add_argument('--lr', type=float, default=1e-4, help='Learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-4, help='Weight decay')
    parser.add_argument('--num_frames', type=int, default=32, help='Number of frames per clip (SlowFast uses 32)')
    parser.add_argument('--num_workers', type=int, default=4, help='DataLoader workers')
    parser.add_argument('--resume', type=str, default=None, help='Path to checkpoint to resume from')
    args = parser.parse_args()

    # Device setup
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")

    # Output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Data transforms (SlowFast uses 256x256 with mean=0.45, std=0.225)
    train_transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize(256),
        transforms.RandomCrop(256),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.45, 0.45, 0.45], std=[0.225, 0.225, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize(256),
        transforms.CenterCrop(256),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.45, 0.45, 0.45], std=[0.225, 0.225, 0.225]),
    ])

    # Datasets
    train_dataset = VideoFrameDataset(
        os.path.join(args.data_dir, 'train'),
        num_frames=args.num_frames,
        transform=train_transform
    )
    val_dataset = VideoFrameDataset(
        os.path.join(args.data_dir, 'val'),
        num_frames=args.num_frames,
        transform=val_transform
    )

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size,
        shuffle=True, num_workers=args.num_workers,
        pin_memory=True, drop_last=True,
        collate_fn=collate_slowfast
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size,
        shuffle=False, num_workers=args.num_workers,
        pin_memory=True,
        collate_fn=collate_slowfast
    )

    print(f"\nTraining samples: {len(train_dataset)}")
    print(f"Validation samples: {len(val_dataset)}")

    # Model — SlowFast-R101 pretrained on Kinetics-400, replace head for 2 classes
    print("Loading SlowFast-R101 pretrained on Kinetics-400...")
    model = torch.hub.load(
        PYTORCHVIDEO_DIR, model='slowfast_r101',
        pretrained=True, source='local'
    )
    # Replace final projection head: 400 classes → 2 classes (normal / suspicious)
    in_features = model.blocks[-1].proj.in_features
    model.blocks[-1].proj = nn.Linear(in_features, 2)
    print(f"Replaced head: {in_features} → 2 classes")

    if args.resume:
        print(f"Resuming from checkpoint: {args.resume}")
        state_dict = torch.load(args.resume, map_location=device, weights_only=True)
        model.load_state_dict(state_dict)

    model = model.to(device)

    # Use DataParallel if multiple GPUs available
    if torch.cuda.device_count() > 1:
        print(f"Using {torch.cuda.device_count()} GPUs!")
        model = nn.DataParallel(model)

    # Loss, optimizer, scheduler
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = GradScaler()

    # Training loop
    best_val_acc = 0.0
    print(f"\n{'='*60}")
    print("Starting Training")
    print(f"{'='*60}\n")

    for epoch in range(1, args.epochs + 1):
        start_time = time.time()

        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler, device, epoch
        )
        val_loss, val_acc = validate(model, val_loader, criterion, device)
        scheduler.step()

        elapsed = time.time() - start_time
        lr = optimizer.param_groups[0]['lr']

        print(f"\nEpoch {epoch}/{args.epochs} ({elapsed:.1f}s) | LR: {lr:.6f}")
        print(f"  Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}%")
        print(f"  Val   Loss: {val_loss:.4f} | Val   Acc: {val_acc:.2f}%")

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            save_model = model.module if hasattr(model, 'module') else model
            save_path = os.path.join(args.output_dir, 'slowfast_r101_finetuned.pth')
            torch.save(save_model.state_dict(), save_path)
            print(f"  ★ Best model saved! Val Acc: {val_acc:.2f}%")

        # Save checkpoint every 5 epochs
        if epoch % 5 == 0:
            save_model = model.module if hasattr(model, 'module') else model
            checkpoint_path = os.path.join(args.output_dir, f'checkpoint_epoch_{epoch}.pth')
            torch.save({
                'epoch': epoch,
                'model_state_dict': save_model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'train_loss': train_loss,
                'val_acc': val_acc,
            }, checkpoint_path)
            print(f"  Checkpoint saved: {checkpoint_path}")

        print()

    print(f"{'='*60}")
    print(f"Training Complete! Best Val Accuracy: {best_val_acc:.2f}%")
    print(f"Model saved to: {os.path.join(args.output_dir, 'slowfast_r101_finetuned.pth')}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
