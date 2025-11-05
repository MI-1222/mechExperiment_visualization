# OpenPIV のデモ 実行方法
## 実行方法
### 0. インストール
[`docs/install.md`](../../docs/install.md)
の`1.3 パッケージをインストール`までを最低限進める。

### 1. 実行設定
`src/execData.jsonc`
の設定を行う。
(`.jsonc`はコメント可能なjsonファイルである。)

### 1.1. デフォルトの実行設定
```json
  // デフォルトの実行設定
  "default_execution": {
    // --config オプションが指定されない場合に実行される設定キー
    "execution_key": "piv_demo",
    // 個別の execution 設定に execution_function がない場合、この設定が適用される。
    "execution_function": {
      "piv_analysis": true, // PIV解析を実行するかどうか
      "create_video": true  // 動画生成を実行するかどうか
    }
  },
```

* `"execution_key"`: 下で設定するどの設定キーを実行するか？
  * 今回は`"piv_demo"`を設定しているので、下で設定された`"piv_demo"`が実行される。
* `"execution_function"`: どの処理を実行するか？
  * `"piv_analysis"`
    * PIV解析を実行するかどうか？
    * `src/lib/open_piv/piv_analysis.py`を実行している。
    * かなり時間がかかる。
    * 今回は`true`に設定しているので、実行される。
  * `"create_video"`
    * 動画生成を実行するかどうか？
    * `src/utils/create_video.py`を実行している。
    * 今回は`true`に設定しているので、実行される。


### 1.2. 個別の実行設定
```json
  // 個別の実行設定リスト
  "executions": {
    "piv_demo": {
      "piv_analysis": {
        "video_path": "demo/piv_demo/piv_demo_input.mp4",
        "output_dir": "demo/piv_demo/mp4_tmp01",
        "scaling_factor": 1.0,
        // `"vmax": null`を指定すると、動画全体の最大速度から自動でスケールが決定される
        "vmax": null,
        "frame_comparison_step": 1,
        "moving_average_window": 5,
        "averaging_method": "median"
      },
      "create_video": {
        "output_dir": "demo/piv_demo",
        "fps": 30,
        "name": "piv_demo_output01.mp4"
      }
    },
  }
```

* `"piv_demo"`
  * 設定キー
  * この文字列を上の`1.1.`の設定で指定する。
  * `"piv_analysis"`
    * `src/lib/open_piv/piv_analysis.py`を実行する際の設定。(そもそも実行するかどうかは`1.1.`で設定。)
    * `"video_path"`: 
      * 解析対象の動画のファイルパス。
    * `"output_dir"`: 
      * 解析結果のベクトル場が表示された画像を保存するディレクトリ。
    * `"scaling_factor"`: 
      * スケーリング係数 (`pixels/mm` など)。
      * 物理的な速度を計算するために使用される。
      * デフォルトは`1.0`。
    * `"vmax"`: 
      * カラーマップの最大値。
      * `null`を指定すると、動画全体の最大速度から自動でスケールが決定される。
      * 特定の値を指定すると、その値でカラーマップが固定される。
    * `"frame_comparison_step"`: PIV解析で比較するフレームの間隔。
      * 例えば`2`に設定すると、フレーム1とフレーム3、フレーム2とフレーム4のように比較する。
      * デフォルトは`1`。
    * `"moving_average_window"`: 
      * 移動平均/中央値のウィンドウサイズ。
      * ベクトル場のノイズを低減するために使用する。
      * 例えば`5`に設定すると、連続する5フレーム分の解析結果を平均/中央値化して、より滑らかなベクトル場を生成する。
      * デフォルトは`1`（集計なし）。
    * `"averaging_method"`: 
      * `moving_average_window`で指定したウィンドウ内での集計方法。
      * `"mean"`（平均）または`"median"`（中央値）が指定できる。
      * 中央値の方が外れ値に対して頑健。デフォルトは`"mean"`。
  * `"create_video"`
    * `src/utils/create_video.py`を実行する際の設定。
    * `"output_dir"`: 
      * 生成された動画を保存するディレクトリ。
    * `"fps"`: 
      * 生成する動画のフレームレート。
    * `"name"`: 
      * 出力する動画のファイル名。


## トラブルシューティング