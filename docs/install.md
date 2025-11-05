# インストールについて

## 0. レポジトリのクローン
```bash
git clone https://github.com/MI-1222/mechExperiment_visualization.git
```

## 1. 仮想環境
### 1.1 python仮想環境の作成
```bash
python3 -m venv .venv
```

### 1.2 仮想環境の起動
```bash
source .venv/bin/activate
```

これにより、
ターミナルのユーザー名の前に`(.venv)`と表示されるようになる。
仮想環境が有効になっていることの確認となる。

### 1.3 パッケージをインストール
```bash
pip install -r requirements.txt --ignore-installed
```

## 2. データのダウンロード
GitHubのレポジトリに動画データを入れたくないので、
[google drive](https://drive.google.com/drive/folders/1Avx0-0aRe4xkkKeQNGTP5eEGAL-wHdgi?usp=drive_link)
からダウンロードして自分の`figure/video/`ディレクトリに配置して下さい。

## 3. `src/main.py`の実行
(ターミナルの前に`(.venv)`が表示されていることを確認。)
```bash
python src/main.py
```