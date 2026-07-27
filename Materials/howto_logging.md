# How to logging with copilot

## 🎯 結論（最短で理解）
**logging を使う基本形：**

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

logger.info("処理開始")
logger.debug("デバッグ情報")
logger.warning("警告")
logger.error("エラー")
logger.critical("致命的エラー")
```

---

## 📌 ログレベル（何を出すかの基準）
- **DEBUG** — 詳細なデバッグ情報  
- **INFO** — 通常の進捗  
- **WARNING** — 想定外だが動く  
- **ERROR** — 処理できない  
- **CRITICAL** — プログラム継続不能  

（Python公式の説明）  [Python](https://docs.python.org/3/howto/logging.html)

---

## 🧱 basicConfig の正しい使い方
**ポイント：basicConfig はプログラムの最初に一度だけ。複数回呼ぶと無視される。**

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    filename="app.log",  # ファイルに出す場合
    filemode="w"         # 上書き or "a" で追記
)
```

（root logger の設定として十分なケースが多い）  [Python](https://docs.python.org/3/library/logging.html)

---

## 🧩 モジュールごとに logger を使う（あなたの Python プロジェクト向け）
あなたは複数ファイルで画像処理や統計をしているので、**getLogger(__name__) を使うのがベスト**。

### main.py
```python
import logging
from processor import process_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

def main():
    logger.info("メイン処理開始")
    process_image("sun.png")
    logger.info("メイン処理終了")

if __name__ == "__main__":
    main()
```

### processor.py
```python
import logging
import numpy as np

logger = logging.getLogger(__name__)

def process_image(path):
    logger.info(f"画像読み込み: {path}")
    arr = np.random.rand(100, 100)
    logger.debug(f"画像 shape={arr.shape}")
    mean = arr.mean()
    logger.info(f"平均値={mean}")
```

---

## 🧪 例：例外をログに書く（画像処理でよく使う）
```python
try:
    do_something()
except Exception:
    logger.exception("画像処理中に例外発生")
```

`logger.exception()` は **traceback を自動で含む**ので便利。  
（公式でも推奨）  [GoLinuxCloud](https://www.golinuxcloud.com/python-logging/)

---

## 📁 ログをファイルに出す（長時間処理に必須）
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("run.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
```

---

## 🔄 ログローテーション（長時間の NumPy / 画像処理で便利）
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "run.log", maxBytes=1_000_000, backupCount=3
)
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)
```

---

## 🧠 よくあるミス（あなたの環境で起きやすい）
- basicConfig を複数回呼んでしまう  
- f-string をログに直接書いてしまう（遅くなる）  
  → `logger.info("mean=%s", mean)` が正しい  
- ロガーのレベルとハンドラのレベルが噛み合わない  
（OpenPython の logging 実践ガイドより）  [openpython.org](https://openpython.org/articles/python-logging-module-guide)

---

## 📚 公式ドキュメント（最も信頼できる）
- **Basic Tutorial**（まず読むべき）  [Python](https://docs.python.org/3/howto/logging.html)  
- **logging モジュール API**（詳細）  [Python](https://docs.python.org/ja/3/library/logging.html)  

---

# with modules
**結論：ログに「どの module から出たログか」を入れるには、`%(name)s` をフォーマットに入れる。**  
これが Python logging の正式な方法で、複数ファイルのプロジェクトでも確実に判別できる。

---

## 🎯 まず最重要ポイント（これだけで解決）
ログフォーマットに **`%(name)s`** を入れると、  
`logger = logging.getLogger(__name__)` で設定した **モジュール名** が自動で入る。

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
```

ログ例：

```
2026-07-28 00:15:12 [INFO] processor: 平均値=0.512
2026-07-28 00:15:12 [INFO] main: メイン処理終了
```

これで **どの module から出たログか一目で分かる**。

---

## 🧩 モジュール構成での実例（あなたの画像処理プロジェクト向け）

### main.py
```python
import logging
from processor import process_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

def main():
    logger.info("メイン処理開始")
    process_image("sun.png")
    logger.info("メイン処理終了")

if __name__ == "__main__":
    main()
```

### processor.py
```python
import logging
import numpy as np

logger = logging.getLogger(__name__)

def process_image(path):
    logger.info(f"画像読み込み: {path}")
    arr = np.random.rand(100, 100)
    logger.debug(f"shape={arr.shape}")
    logger.info(f"平均値={arr.mean()}")
```

ログファイルにはこう出る：

```
[INFO] main: メイン処理開始
[INFO] processor: 画像読み込み: sun.png
[INFO] processor: 平均値=0.512
[INFO] main: メイン処理終了
```

---

## 🔍 さらに細かく識別したい場合（高度なフォーマット）
### 1. ファイル名を入れる
```python
format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d %(name)s: %(message)s"
```

例：

```
processor.py:12 processor: 平均値=0.512
```

### 2. 関数名を入れる
```python
format="%(asctime)s [%(levelname)s] %(name)s %(funcName)s: %(message)s"
```

---

## 🧠 よくある落とし穴（あなたの環境で起きやすい）
- **basicConfig を複数回呼ぶとフォーマットが反映されない**  
  → 最初の1回だけ有効
- **logger = logging.getLogger(__name__) を使わずに root logger を使ってしまう**  
  → すべてのログが同じ名前になる
- **tqdm と logging が混ざってログが崩れる**  
  → tqdm.write() を使うと綺麗に共存できる

---

## 📌 まとめ
- ログフォーマットに **`%(name)s`** を入れる  
- 各モジュールで **`logger = logging.getLogger(__name__)`** を使う  
- これでログファイルから **どの module のログか確実に判別できる**

---