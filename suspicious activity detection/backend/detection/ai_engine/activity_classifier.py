"""
SlowFast-R101 Activity Classification Module.
Classifies human activity using pretrained SlowFast-R101 from pytorchvideo.
Uses 32-frame sliding window split into slow (8 frames) and fast (32 frames) pathways.
Pretrained on Kinetics-400 (400 action classes, 77.9% top-1 accuracy).
"""
import logging
import os
import sys

import cv2
import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger('detection')

# ---------------------------------------------------------------------------
# Kinetics-400 class labels (official ordering from kinetics_classnames.json)
# ---------------------------------------------------------------------------
KINETICS_400_LABELS = [
    "abseiling",                                        # 0
    "air drumming",                                     # 1
    "answering questions",                              # 2
    "applauding",                                       # 3
    "applying cream",                                   # 4
    "archery",                                          # 5
    "arm wrestling",                                    # 6
    "arranging flowers",                                # 7
    "assembling computer",                              # 8
    "auctioning",                                       # 9
    "baby waking up",                                   # 10
    "baking cookies",                                   # 11
    "balloon blowing",                                  # 12
    "bandaging",                                        # 13
    "barbequing",                                       # 14
    "bartending",                                       # 15
    "beatboxing",                                       # 16
    "bee keeping",                                      # 17
    "belly dancing",                                    # 18
    "bench pressing",                                   # 19
    "bending back",                                     # 20
    "bending metal",                                    # 21
    "biking through snow",                              # 22
    "blasting sand",                                    # 23
    "blowing glass",                                    # 24
    "blowing leaves",                                   # 25
    "blowing nose",                                     # 26
    "blowing out candles",                              # 27
    "bobsledding",                                      # 28
    "bookbinding",                                      # 29
    "bouncing on trampoline",                           # 30
    "bowling",                                          # 31
    "braiding hair",                                    # 32
    "breading or breadcrumbing",                        # 33
    "breakdancing",                                     # 34
    "brush painting",                                   # 35
    "brushing hair",                                    # 36
    "brushing teeth",                                   # 37
    "building cabinet",                                 # 38
    "building shed",                                    # 39
    "bungee jumping",                                   # 40
    "busking",                                          # 41
    "canoeing or kayaking",                             # 42
    "capoeira",                                         # 43
    "carrying baby",                                    # 44
    "cartwheeling",                                     # 45
    "carving pumpkin",                                  # 46
    "catching fish",                                    # 47
    "catching or throwing baseball",                    # 48
    "catching or throwing frisbee",                     # 49
    "catching or throwing softball",                    # 50
    "celebrating",                                      # 51
    "changing oil",                                     # 52
    "changing wheel",                                   # 53
    "checking tires",                                   # 54
    "cheerleading",                                     # 55
    "chopping wood",                                    # 56
    "clapping",                                         # 57
    "clay pottery making",                              # 58
    "clean and jerk",                                   # 59
    "cleaning floor",                                   # 60
    "cleaning gutters",                                 # 61
    "cleaning pool",                                    # 62
    "cleaning shoes",                                   # 63
    "cleaning toilet",                                  # 64
    "cleaning windows",                                 # 65
    "climbing a rope",                                  # 66
    "climbing ladder",                                  # 67
    "climbing tree",                                    # 68
    "contact juggling",                                 # 69
    "cooking chicken",                                  # 70
    "cooking egg",                                      # 71
    "cooking on campfire",                              # 72
    "cooking sausages",                                 # 73
    "counting money",                                   # 74
    "country line dancing",                             # 75
    "cracking neck",                                    # 76
    "crawling baby",                                    # 77
    "crossing river",                                   # 78
    "crying",                                           # 79
    "curling hair",                                     # 80
    "cutting nails",                                    # 81
    "cutting pineapple",                                # 82
    "cutting watermelon",                               # 83
    "dancing ballet",                                   # 84
    "dancing charleston",                               # 85
    "dancing gangnam style",                            # 86
    "dancing macarena",                                 # 87
    "deadlifting",                                      # 88
    "decorating the christmas tree",                    # 89
    "digging",                                          # 90
    "dining",                                           # 91
    "disc golfing",                                     # 92
    "diving cliff",                                     # 93
    "dodgeball",                                        # 94
    "doing aerobics",                                   # 95
    "doing laundry",                                    # 96
    "doing nails",                                      # 97
    "drawing",                                          # 98
    "dribbling basketball",                             # 99
    "drinking",                                         # 100
    "drinking beer",                                    # 101
    "drinking shots",                                   # 102
    "driving car",                                      # 103
    "driving tractor",                                  # 104
    "drop kicking",                                     # 105
    "drumming fingers",                                 # 106
    "dunking basketball",                               # 107
    "dying hair",                                       # 108
    "eating burger",                                    # 109
    "eating cake",                                      # 110
    "eating carrots",                                   # 111
    "eating chips",                                     # 112
    "eating doughnuts",                                 # 113
    "eating hotdog",                                    # 114
    "eating ice cream",                                 # 115
    "eating spaghetti",                                 # 116
    "eating watermelon",                                # 117
    "egg hunting",                                      # 118
    "exercising arm",                                   # 119
    "exercising with an exercise ball",                 # 120
    "extinguishing fire",                               # 121
    "faceplanting",                                     # 122
    "feeding birds",                                    # 123
    "feeding fish",                                     # 124
    "feeding goats",                                    # 125
    "filling eyebrows",                                 # 126
    "finger snapping",                                  # 127
    "fixing hair",                                      # 128
    "flipping pancake",                                 # 129
    "flying kite",                                      # 130
    "folding clothes",                                  # 131
    "folding napkins",                                  # 132
    "folding paper",                                    # 133
    "front raises",                                     # 134
    "frying vegetables",                                # 135
    "garbage collecting",                               # 136
    "gargling",                                         # 137
    "getting a haircut",                                # 138
    "getting a tattoo",                                 # 139
    "giving or receiving award",                        # 140
    "golf chipping",                                    # 141
    "golf driving",                                     # 142
    "golf putting",                                     # 143
    "grinding meat",                                    # 144
    "grooming dog",                                     # 145
    "grooming horse",                                   # 146
    "gymnastics tumbling",                              # 147
    "hammer throw",                                     # 148
    "headbanging",                                      # 149
    "headbutting",                                      # 150
    "high jump",                                        # 151
    "high kick",                                        # 152
    "hitting baseball",                                 # 153
    "hockey stop",                                      # 154
    "holding snake",                                    # 155
    "hopscotch",                                        # 156
    "hoverboarding",                                    # 157
    "hugging",                                          # 158
    "hula hooping",                                     # 159
    "hurdling",                                         # 160
    "hurling (sport)",                                  # 161
    "ice climbing",                                     # 162
    "ice fishing",                                      # 163
    "ice skating",                                      # 164
    "ironing",                                          # 165
    "javelin throw",                                    # 166
    "jetskiing",                                        # 167
    "jogging",                                          # 168
    "juggling balls",                                   # 169
    "juggling fire",                                    # 170
    "juggling soccer ball",                             # 171
    "jumping into pool",                                # 172
    "jumpstyle dancing",                                # 173
    "kicking field goal",                               # 174
    "kicking soccer ball",                              # 175
    "kissing",                                          # 176
    "kitesurfing",                                      # 177
    "knitting",                                         # 178
    "krumping",                                         # 179
    "laughing",                                         # 180
    "laying bricks",                                    # 181
    "long jump",                                        # 182
    "lunge",                                            # 183
    "making a cake",                                    # 184
    "making a sandwich",                                # 185
    "making bed",                                       # 186
    "making jewelry",                                   # 187
    "making pizza",                                     # 188
    "making snowman",                                   # 189
    "making sushi",                                     # 190
    "making tea",                                       # 191
    "marching",                                         # 192
    "massaging back",                                   # 193
    "massaging feet",                                   # 194
    "massaging legs",                                   # 195
    "massaging person's head",                          # 196
    "milking cow",                                      # 197
    "mopping floor",                                    # 198
    "motorcycling",                                     # 199
    "moving furniture",                                 # 200
    "mowing lawn",                                      # 201
    "news anchoring",                                   # 202
    "opening bottle",                                   # 203
    "opening present",                                  # 204
    "paragliding",                                      # 205
    "parasailing",                                      # 206
    "parkour",                                          # 207
    "passing American football (in game)",              # 208
    "passing American football (not in game)",          # 209
    "peeling apples",                                   # 210
    "peeling potatoes",                                 # 211
    "petting animal (not cat)",                         # 212
    "petting cat",                                      # 213
    "picking fruit",                                    # 214
    "planting trees",                                   # 215
    "plastering",                                       # 216
    "playing accordion",                                # 217
    "playing badminton",                                # 218
    "playing bagpipes",                                 # 219
    "playing basketball",                               # 220
    "playing bass guitar",                              # 221
    "playing cards",                                    # 222
    "playing cello",                                    # 223
    "playing chess",                                    # 224
    "playing clarinet",                                 # 225
    "playing controller",                               # 226
    "playing cricket",                                  # 227
    "playing cymbals",                                  # 228
    "playing didgeridoo",                               # 229
    "playing drums",                                    # 230
    "playing flute",                                    # 231
    "playing guitar",                                   # 232
    "playing harmonica",                                # 233
    "playing harp",                                     # 234
    "playing ice hockey",                               # 235
    "playing keyboard",                                 # 236
    "playing kickball",                                 # 237
    "playing monopoly",                                 # 238
    "playing organ",                                    # 239
    "playing paintball",                                # 240
    "playing piano",                                    # 241
    "playing poker",                                    # 242
    "playing recorder",                                 # 243
    "playing saxophone",                                # 244
    "playing squash or racquetball",                    # 245
    "playing tennis",                                   # 246
    "playing trombone",                                 # 247
    "playing trumpet",                                  # 248
    "playing ukulele",                                  # 249
    "playing violin",                                   # 250
    "playing volleyball",                               # 251
    "playing xylophone",                                # 252
    "pole vault",                                       # 253
    "presenting weather forecast",                      # 254
    "pull ups",                                         # 255
    "pumping fist",                                     # 256
    "pumping gas",                                      # 257
    "punching bag",                                     # 258
    "punching person (boxing)",                         # 259
    "push up",                                          # 260
    "pushing car",                                      # 261
    "pushing cart",                                     # 262
    "pushing wheelchair",                               # 263
    "reading book",                                     # 264
    "reading newspaper",                                # 265
    "recording music",                                  # 266
    "riding a bike",                                    # 267
    "riding camel",                                     # 268
    "riding elephant",                                  # 269
    "riding mechanical bull",                           # 270
    "riding mountain bike",                             # 271
    "riding mule",                                      # 272
    "riding or walking with horse",                     # 273
    "riding scooter",                                   # 274
    "riding unicycle",                                  # 275
    "ripping paper",                                    # 276
    "robot dancing",                                    # 277
    "rock climbing",                                    # 278
    "rock scissors paper",                              # 279
    "roller skating",                                   # 280
    "running on treadmill",                             # 281
    "sailing",                                          # 282
    "salsa dancing",                                    # 283
    "sanding floor",                                    # 284
    "scrambling eggs",                                  # 285
    "scuba diving",                                     # 286
    "setting table",                                    # 287
    "shaking hands",                                    # 288
    "shaking head",                                     # 289
    "sharpening knives",                                # 290
    "sharpening pencil",                                # 291
    "shaving head",                                     # 292
    "shaving legs",                                     # 293
    "shearing sheep",                                   # 294
    "shining shoes",                                    # 295
    "shooting basketball",                              # 296
    "shooting goal (soccer)",                           # 297
    "shot put",                                         # 298
    "shoveling snow",                                   # 299
    "shredding paper",                                  # 300
    "shuffling cards",                                  # 301
    "side kick",                                        # 302
    "sign language interpreting",                       # 303
    "singing",                                          # 304
    "situp",                                            # 305
    "skateboarding",                                    # 306
    "ski jumping",                                      # 307
    "skiing (not slalom or crosscountry)",              # 308
    "skiing crosscountry",                              # 309
    "skiing slalom",                                    # 310
    "skipping rope",                                    # 311
    "skydiving",                                        # 312
    "slacklining",                                      # 313
    "slapping",                                         # 314
    "sled dog racing",                                  # 315
    "smoking",                                          # 316
    "smoking hookah",                                   # 317
    "snatch weight lifting",                            # 318
    "sneezing",                                         # 319
    "sniffing",                                         # 320
    "snorkeling",                                       # 321
    "snowboarding",                                     # 322
    "snowkiting",                                       # 323
    "snowmobiling",                                     # 324
    "somersaulting",                                    # 325
    "spinning poi",                                     # 326
    "spray painting",                                   # 327
    "spraying",                                         # 328
    "springboard diving",                               # 329
    "squat",                                            # 330
    "sticking tongue out",                              # 331
    "stomping grapes",                                  # 332
    "stretching arm",                                   # 333
    "stretching leg",                                   # 334
    "strumming guitar",                                 # 335
    "surfing crowd",                                    # 336
    "surfing water",                                    # 337
    "sweeping floor",                                   # 338
    "swimming backstroke",                              # 339
    "swimming breast stroke",                           # 340
    "swimming butterfly stroke",                        # 341
    "swing dancing",                                    # 342
    "swinging legs",                                    # 343
    "swinging on something",                            # 344
    "sword fighting",                                   # 345
    "tai chi",                                          # 346
    "taking a shower",                                  # 347
    "tango dancing",                                    # 348
    "tap dancing",                                      # 349
    "tapping guitar",                                   # 350
    "tapping pen",                                      # 351
    "tasting beer",                                     # 352
    "tasting food",                                     # 353
    "testifying",                                       # 354
    "texting",                                          # 355
    "throwing axe",                                     # 356
    "throwing ball",                                    # 357
    "throwing discus",                                  # 358
    "tickling",                                         # 359
    "tobogganing",                                      # 360
    "tossing coin",                                     # 361
    "tossing salad",                                    # 362
    "training dog",                                     # 363
    "trapezing",                                        # 364
    "trimming or shaving beard",                        # 365
    "trimming trees",                                   # 366
    "triple jump",                                      # 367
    "tying bow tie",                                    # 368
    "tying knot (not on a tie)",                        # 369
    "tying tie",                                        # 370
    "unboxing",                                         # 371
    "unloading truck",                                  # 372
    "using computer",                                   # 373
    "using remote controller (not gaming)",             # 374
    "using segway",                                     # 375
    "vault",                                            # 376
    "waiting in line",                                  # 377
    "walking the dog",                                  # 378
    "washing dishes",                                   # 379
    "washing feet",                                     # 380
    "washing hair",                                     # 381
    "washing hands",                                    # 382
    "water skiing",                                     # 383
    "water sliding",                                    # 384
    "watering plants",                                  # 385
    "waxing back",                                      # 386
    "waxing chest",                                     # 387
    "waxing eyebrows",                                  # 388
    "waxing legs",                                      # 389
    "weaving basket",                                   # 390
    "welding",                                          # 391
    "whistling",                                        # 392
    "windsurfing",                                      # 393
    "wrapping present",                                 # 394
    "wrestling",                                        # 395
    "writing",                                          # 396
    "yawning",                                          # 397
    "yoga",                                             # 398
    "zumba",                                            # 399
]

# ---------------------------------------------------------------------------
# Activities flagged as SUSPICIOUS / FIGHTING in a CCTV surveillance context
# IMPORTANT: Only Kinetics-400 labels that genuinely indicate violence,
# aggression, or danger in a CCTV context.  Sports (baseball, soccer,
# basketball, gymnastics, etc.) are intentionally EXCLUDED to avoid
# false positives.  Ghost labels not present in Kinetics-400 have been
# removed (e.g. "kickboxing", "jousting").
# ---------------------------------------------------------------------------

# VIOLENT: Direct physical violence / weapon use — always flag
VIOLENT_ACTIVITIES = {
    "punching person (boxing)",   # physical assault
    "slapping",                    # physical assault
    "headbutting",                 # physical assault
    "sword fighting",              # weapon violence
    "throwing axe",                # weapon throwing
}

# AGGRESSIVE: Potentially dangerous — flag with higher confidence
AGGRESSIVE_ACTIVITIES = {
    "drop kicking",                # aggressive kick attack
    "high kick",                   # aggressive kick motion
    "side kick",                   # aggressive kick motion
    "spray painting",              # vandalism indicator
    "sharpening knives",           # weapon preparation
    "wrestling",                   # ground fighting in CCTV context
}

# Combined set used for probability aggregation
SUSPICIOUS_ACTIVITIES = VIOLENT_ACTIVITIES | AGGRESSIVE_ACTIVITIES

# ---------------------------------------------------------------------------
# Activities that are clearly NORMAL in CCTV context — boosts confidence
# that a scene is safe when these dominate the prediction.
# ---------------------------------------------------------------------------
NORMAL_ACTIVITIES = {
    # --- Everyday actions ---
    "answering questions", "applauding", "arranging flowers",
    "baking cookies", "barbequing", "bartending", "bookbinding",
    "braiding hair", "brushing hair", "brushing teeth",
    "carrying baby", "celebrating", "checking tires", "clapping",
    "cleaning floor", "cleaning shoes", "cleaning windows",
    "cooking chicken", "cooking egg", "cooking on campfire", "cooking sausages",
    "counting money", "cutting nails", "cutting pineapple", "cutting watermelon",
    "decorating the christmas tree", "dining", "doing laundry", "doing nails",
    "drawing", "drinking", "drinking beer",
    # --- Eating ---
    "eating burger", "eating cake", "eating carrots",
    "eating chips", "eating doughnuts", "eating hotdog", "eating ice cream",
    "eating spaghetti", "eating watermelon",
    # --- Sitting / standing ---
    "reading book", "reading newspaper", "using computer",
    "using remote controller (not gaming)", "texting", "waiting in line",
    "writing", "yawning",
    # --- Walking / moving normally ---
    "walking the dog", "jogging", "riding a bike", "riding scooter",
    # --- Self-care ---
    "getting a haircut", "washing dishes", "washing feet",
    "washing hair", "washing hands", "watering plants",
    "ironing", "folding clothes", "making bed",
    # --- Social ---
    "hugging", "kissing", "shaking hands", "singing", "laughing",
    "giving or receiving award", "testifying", "wrapping present",
    # --- Music / art ---
    "playing accordion", "playing guitar", "playing piano",
    "playing violin", "playing drums", "playing flute",
    "playing keyboard", "playing cello", "playing saxophone",
    "playing trumpet", "playing ukulele", "playing harmonica",
    "playing harp", "playing recorder", "playing organ",
    "playing bass guitar", "playing bagpipes", "playing clarinet",
    "playing xylophone", "playing trombone", "playing didgeridoo",
    "recording music", "strumming guitar",
    # --- Games / relaxation ---
    "playing cards", "playing chess", "playing monopoly", "playing poker",
    "playing controller", "bowling",
    # --- Relaxed sports ---
    "golf chipping", "golf driving", "golf putting",
    "stretching arm", "stretching leg", "tai chi", "yoga", "zumba",
    "exercising arm", "exercising with an exercise ball",
}


class SlowFastClassifier:
    """
    Activity classification using SlowFast-R101 pretrained on Kinetics-400.

    Dual-pathway architecture:
      - Slow pathway: 8 frames (temporal stride α=4 from 32 input frames)
      - Fast pathway: 32 frames (all frames)

    Accuracy features:
      - 256px short-side resize + center crop (matches training distribution)
      - Tiered decision: VIOLENT > AGGRESSIVE > aggregated > top-3 check
      - Minimum confidence floors prevent low-confidence false positives
      - Only 11 truly dangerous activities flagged (sports excluded)
    """

    # SlowFast preprocessing constants (official PyTorchVideo training config)
    # 256px matches the model's training resolution for maximum accuracy
    SIDE_SIZE = 256
    CROP_SIZE = 256
    MEAN = [0.45, 0.45, 0.45]
    STD = [0.225, 0.225, 0.225]
    NUM_FRAMES = 32
    ALPHA = 4  # temporal stride for slow pathway

    # Tiered confidence floors for suspicious detection
    VIOLENT_CONF_FLOOR = 0.08     # low bar — violence must be caught early
    AGGRESSIVE_CONF_FLOOR = 0.15  # moderate — need some certainty
    SUSPICIOUS_AGG_THRESHOLD = 0.35  # aggregated sus prob must beat normal prob

    def __init__(self, device=None, confidence_threshold=0.6, top_k=5):
        """
        Args:
            device: 'cuda', 'cpu', or None for auto
            confidence_threshold: minimum confidence for suspicious flag
            top_k: number of top predictions to return
        """
        self.confidence_threshold = confidence_threshold
        self.top_k = top_k
        self.model = None

        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Pre-compute normalisation tensors (avoids per-frame Python loop)
        self._mean = torch.tensor(self.MEAN).view(3, 1, 1)
        self._std = torch.tensor(self.STD).view(3, 1, 1)

        # Pre-compute slow pathway indices
        self._slow_indices = torch.linspace(
            0, self.NUM_FRAMES - 1, self.NUM_FRAMES // self.ALPHA
        ).long()

        self._load_model()

        # Build index caches for fast probability aggregation
        self._violent_indices = [
            i for i, l in enumerate(KINETICS_400_LABELS)
            if l in VIOLENT_ACTIVITIES
        ]
        self._aggressive_indices = [
            i for i, l in enumerate(KINETICS_400_LABELS)
            if l in AGGRESSIVE_ACTIVITIES
        ]
        self._suspicious_indices = [
            i for i, l in enumerate(KINETICS_400_LABELS)
            if l in SUSPICIOUS_ACTIVITIES
        ]
        self._normal_indices = [
            i for i, l in enumerate(KINETICS_400_LABELS)
            if l in NORMAL_ACTIVITIES
        ]

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------
    def _load_model(self):
        """Load SlowFast-R101 pretrained on Kinetics-400 via torch.hub (local)."""
        try:
            # Resolve path to the local pytorchvideo checkout
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', '..')
            )
            pytorchvideo_dir = os.path.join(project_root, 'pytorchvideo-main')

            if not os.path.isdir(pytorchvideo_dir):
                raise FileNotFoundError(
                    f"pytorchvideo-main directory not found at {pytorchvideo_dir}"
                )

            logger.info("Loading SlowFast-R101 pretrained on Kinetics-400 ...")

            # torch.hub.load with source='local' adds the dir to sys.path
            # and invokes hubconf.py → slowfast_r101(pretrained=True)
            self.model = torch.hub.load(
                pytorchvideo_dir,
                model='slowfast_r101',
                pretrained=True,
                source='local',
            )

            self.model = self.model.to(self.device)
            self.model.eval()

            total_params = sum(p.numel() for p in self.model.parameters())
            logger.info(
                f"SlowFast-R101 loaded on {self.device} "
                f"({total_params / 1e6:.1f}M params, 400 Kinetics classes)"
            )

        except Exception as e:
            logger.error(f"Failed to load SlowFast-R101: {e}")
            raise

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------
    def preprocess_frames(self, frames):
        """
        Preprocess a list of frames for SlowFast-R101 (accuracy-optimised).

        Steps:
          1. Pad / trim to exactly 32 frames
          2. BGR -> RGB, short-side resize to 256, center crop 256×256
             (matches the model's training distribution for best accuracy)
          3. Batch-normalise with pre-computed mean/std tensors
          4. PackPathway -> [slow (1,3,8,256,256), fast (1,3,32,256,256)]

        Args:
            frames: list of numpy arrays (BGR, any size)

        Returns:
            list of two tensors: [slow_pathway, fast_pathway]
        """
        n = len(frames)
        # Ensure exactly NUM_FRAMES frames by repeating last or trimming
        if n < self.NUM_FRAMES:
            pad = self.NUM_FRAMES - n
            last = frames[-1]
            frames = frames + [last] * pad
        elif n > self.NUM_FRAMES:
            frames = frames[:self.NUM_FRAMES]

        # Process each frame: short-side resize → center crop (matches training)
        buf = np.empty((self.NUM_FRAMES, self.CROP_SIZE, self.CROP_SIZE, 3), dtype=np.float32)
        for i, frame in enumerate(frames):
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            # Short-side resize: scale so shorter dimension = SIDE_SIZE
            if h <= w:
                new_h = self.SIDE_SIZE
                new_w = int(w * self.SIDE_SIZE / h)
            else:
                new_w = self.SIDE_SIZE
                new_h = int(h * self.SIDE_SIZE / w)
            rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            # Center crop to CROP_SIZE × CROP_SIZE
            y_off = (new_h - self.CROP_SIZE) // 2
            x_off = (new_w - self.CROP_SIZE) // 2
            buf[i] = rgb[y_off:y_off + self.CROP_SIZE, x_off:x_off + self.CROP_SIZE]

        # (32, H, W, 3) -> tensor (32, 3, H, W) -> (3, 32, H, W)
        video_tensor = torch.from_numpy(buf).permute(0, 3, 1, 2) / 255.0  # (32,3,H,W)
        video_tensor = (video_tensor - self._mean) / self._std              # normalise
        video_tensor = video_tensor.permute(1, 0, 2, 3)                     # (3,32,H,W)

        # PackPathway using pre-computed indices
        slow_pathway = torch.index_select(video_tensor, 1, self._slow_indices)

        # Add batch dim and move to device in one call
        return [
            slow_pathway.unsqueeze(0).to(self.device),   # (1,3,8,256,256)
            video_tensor.unsqueeze(0).to(self.device),   # (1,3,32,256,256)
        ]

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    def classify_activity(self, frames):
        """
        Classify activity from a sliding window of person crops.

        Uses a **tiered decision system** to minimise false positives:
          - Tier 1: Top-1 is VIOLENT  with confidence >= 8%  → suspicious
          - Tier 2: Top-1 is AGGRESSIVE with confidence >= 15% → suspicious
          - Tier 3: Aggregated suspicious prob >= 35% AND > normal  → suspicious
          - Tier 4: Any top-3 prediction is VIOLENT with >= 5%     → suspicious
          - Default: normal

        Args:
            frames: list of numpy arrays (person crops, BGR).
                    Ideally 32 frames; padded automatically if fewer.

        Returns:
            dict with label, activity, confidence, top_activities, probabilities
        """
        if not frames:
            return self._default_result()

        try:
            with torch.inference_mode():
                inputs = self.preprocess_frames(list(frames))
                preds = self.model(inputs)
                probs = torch.softmax(preds, dim=1)

            # Work on CPU numpy once
            all_probs = probs[0].cpu().numpy()

            # Top-k predictions
            top_k_indices = np.argpartition(all_probs, -self.top_k)[-self.top_k:]
            top_k_indices = top_k_indices[np.argsort(all_probs[top_k_indices])[::-1]]

            labels = KINETICS_400_LABELS
            top_activities = [
                (labels[i] if i < len(labels) else f"class_{i}",
                 round(float(all_probs[i]), 4))
                for i in top_k_indices
            ]

            best_activity = top_activities[0][0]
            best_confidence = top_activities[0][1]

            # Aggregated probabilities per category
            violent_prob = float(all_probs[self._violent_indices].sum()) \
                if self._violent_indices else 0.0
            aggressive_prob = float(all_probs[self._aggressive_indices].sum()) \
                if self._aggressive_indices else 0.0
            suspicious_prob = float(all_probs[self._suspicious_indices].sum()) \
                if self._suspicious_indices else 0.0
            normal_mapped_prob = float(all_probs[self._normal_indices].sum()) \
                if self._normal_indices else 0.0

            # --- Tiered decision logic (reduces false positives) ---
            is_suspicious = False
            trigger = "normal"

            # Tier 1: Top-1 is VIOLENT with enough confidence
            if (best_activity in VIOLENT_ACTIVITIES
                    and best_confidence >= self.VIOLENT_CONF_FLOOR):
                is_suspicious = True
                trigger = f"violent_top1({best_activity}:{best_confidence:.3f})"

            # Tier 2: Top-1 is AGGRESSIVE with higher confidence
            elif (best_activity in AGGRESSIVE_ACTIVITIES
                  and best_confidence >= self.AGGRESSIVE_CONF_FLOOR):
                is_suspicious = True
                trigger = f"aggressive_top1({best_activity}:{best_confidence:.3f})"

            # Tier 3: Aggregated suspicious prob dominates normal prob
            elif (suspicious_prob >= self.SUSPICIOUS_AGG_THRESHOLD
                  and suspicious_prob > normal_mapped_prob):
                is_suspicious = True
                trigger = (f"aggregated(sus={suspicious_prob:.3f}"
                           f">norm={normal_mapped_prob:.3f})")

            # Tier 4: Any top-3 is VIOLENT with >= 5% probability
            else:
                for act_name, act_prob in top_activities[:3]:
                    if act_name in VIOLENT_ACTIVITIES and act_prob >= 0.05:
                        is_suspicious = True
                        trigger = f"violent_top3({act_name}:{act_prob:.3f})"
                        break

            # When flagged suspicious, show the top *suspicious* activity
            # instead of the overall top-1 (which may be a harmless activity
            # like "drinking").  This prevents the red box from displaying
            # a normal-looking label.
            if is_suspicious and best_activity not in SUSPICIOUS_ACTIVITIES:
                # Find the highest-probability suspicious activity
                sus_best_name = None
                sus_best_prob = 0.0
                for idx in self._suspicious_indices:
                    p = float(all_probs[idx])
                    if p > sus_best_prob:
                        sus_best_prob = p
                        sus_best_name = labels[idx]
                if sus_best_name:
                    display_activity = sus_best_name
                    display_confidence = round(sus_best_prob, 4)
                else:
                    display_activity = best_activity
                    display_confidence = round(best_confidence, 4)
            else:
                display_activity = best_activity
                display_confidence = round(best_confidence, 4)

            result = {
                'label': 'suspicious' if is_suspicious else 'normal',
                'activity': display_activity,
                'confidence': display_confidence,
                'top_activities': top_activities,
                'probabilities': {
                    'normal': round(1.0 - suspicious_prob, 4),
                    'suspicious': round(suspicious_prob, 4),
                },
            }

            logger.debug(
                f"Activity: {best_activity} ({best_confidence:.3f}) "
                f"-> {trigger} | display={display_activity} "
                f"[viol={violent_prob:.3f}, aggr={aggressive_prob:.3f}, "
                f"sus={suspicious_prob:.3f}, norm={normal_mapped_prob:.3f}]"
            )
            return result

        except Exception as e:
            logger.error(f"Error during activity classification: {e}")
            return self._default_result()

    @staticmethod
    def _default_result():
        return {
            'label': 'normal',
            'activity': 'unknown',
            'confidence': 0.0,
            'top_activities': [],
            'probabilities': {'normal': 1.0, 'suspicious': 0.0},
        }
