# asiCAMtest

高校2年 島野淳  
2026.07.10
>
>[!WARNING]
> これらの英訳には、機械翻訳およびAIによる翻訳が含まれています。
>
> These English translations include machine translations and AI-generated translations.

## Background 背景

我々は、太陽の観測にZWO ASIカメラ[^1]を使用しています。  
これまでは自作のデスクトップパソコンを用いて観測を行っていましたが日々の黒点の観測方法をスケッチから動画撮影へと移行することに伴い、撮影に学校貸与のノートパソコンを用いることにしました。取り回しが良いからです。

We use a ZWO ASI camera[^1] for solar observations.  
Previously, we conducted observations using a custom-built desktop computer. However, as we transitioned our daily sunspot observation method from sketching to video recording, we decided to use a school-issued laptop for capturing footage due to its portability and ease of handling.

しかし、このパソコンには問題がありました。  
カメラを接続後、少し間が空くとカメラが使用できなくなるのです。[^2]

However, there was an issue with this laptop.  
If the camera was left idle for a short period after connection, it would become unavailable.[^2]

この問題は、黒点撮影時に太陽の移動方向を画像左向きに統一するための自作プログラムの試験中に発覚しました。  
しかし、ASI_Cap[^3]でカメラの探索中にカメラを接続・起動すればカメラがその後も使用できることがわかりました。

This issue was discovered during testing of a self-made program designed to keep the sun's movement direction consistently oriented toward the left of the image during sunspot photography.  
However, we found that if the camera was connected and launched while ASICap[^3] was actively searching for cameras, it remained usable afterward.

このことから、カメラ接続後に取り外し準備が行われる前に取り外せば使用できるという仮説を立て、  
カメラを探索し、接続された瞬間に起動することがカメラを使用する鍵であると考えました。

Based on this, we hypothesized that the camera could be used if it is initialized after being connected but before the system prepares it for removal.  
Therefore, we concluded that the key to utilizing the camera is to continuously scan for it and launch it the exact moment it is connected.

[^1]:[ASI432MM](https://www.bing.com/ck/a?!&&p=37019ba05556b3272ce273824f5dd1ecaf41b8d1767b56a37fecfda65a039d73JmltdHM9MTc4MzU1NTIwMA&ptn=3&ver=2&hsh=4&fclid=0218a384-e0a7-693d-2227-b575e1c96879&psq=ASI432MM&u=a1aHR0cHM6Ly93d3cuendvYXN0cm8uY29tL3Byb2R1Y3QvendvLWFzaTQzMm1tLw)

[^2]:>このハードウェア デバイスをコンピューターから取り外す準備が行われているがまだ取り外されていないため、そのデバイスを使用できません。 (コード 47)
    >
    >この問題を解決するには、デバイスを取り外してから再度取り付ける必要があります。  

    デバイスマネージャ>ZWO ASI432MM Cameraのプロパティ>デバイスの状態
    > This hardware device cannot be used because it is prepared to be removed from the computer but has not been removed yet. (Code 47)
    >
    > To fix this problem, disconnect the device from your computer and then plug it in again.

    Device Manager > ZWO ASI432MM Camera Properties > Device status

[^3]:[ASICap_V2.18(64bit)](https://www.bing.com/ck/a?!&&p=bd83e778ffa244a8905226692de98954c856feff92046dec67c1ab3b31317ff6JmltdHM9MTc4MzU1NTIwMA&ptn=3&ver=2&hsh=4&fclid=0218a384-e0a7-693d-2227-b575e1c96879&psq=ASICap&u=a1aHR0cHM6Ly93d3cuendvYXN0cm8uY29tL3NvZnR3YXJlLw)

## Aim 目的

今回作成した`zwoasiCAM_connect_test`及び`zwoasiCAM_connect_test.v.01.0.0.zip`は先述の仮設をもとに、

**カメラを探索し続けていれば接続・使用できるのか**

を検証するためのシンプルなものです。

Based on the aforementioned hypothesis, `zwoasiCAM_connect_test` and `zwoasiCAM_connect_test.v.01.0.0.zip` created for this project are simple tools designed to verify:

**Whether the camera can be successfully connected and used if we keep continuously searching for it.**

### SubAim 副目標

pythonファイルのexe化についての検証をしています。
We are verifying the executable (.exe) file.　　

- exeをshortcutから実行するための絶対パス設定

- Absolute path configuration to run the .exe file from a shortcut:

```python
if getattr(sys, "frozen", False):
    # exeを実行している場合
    # If running as an executable file
    base_dir = os.path.dirname(sys.executable)
else:
    # 通常のpythonスクリプトとして実行している場合
    # If running as a standard Python script
    base_dir = os.path.dirname(os.path.abspath(__file__))

dll_path = os.path.join(base_dir, "ASICamera2.dll")
```

## How to Use 使用方法

学校貸与パソコンはpythonのインストールができないのでexefileを使用しました。

1. exeを起動
2. カメラを接続(物理)
3. カメラプレビュー表示

非常にシンプルです。python実行においても同様です。

Since Python cannot be installed on the school-issued laptop, we used the executable (.exe) file.

1. Launch the .exe file.
2. Connect the camera (physically).
3. The camera preview will be displayed.

It is extremely simple. The process is identical when running it as a Python script.

## Results 結果

保有しているasiカメラ[^1]は2台あるが、いづれも問題なく接続が可能でした。

1. **カメラ未接続状態で**本ソフトを実行
2. 接続待機中にカメラを接続

という手順が、カメラ取り出し準備前に接続することで、カメラの使用を可能にしているといえます。

We own two ASI cameras[^1], and both were able to connect without any issues.
Following the procedure:

1. Run the software while the camera is not connected,
2. Connect the camera during the waiting phase,

we confirmed that this sequence allows the camera to be used successfully by ensuring it is initialized before the system prepares it for removal.
These results support the hypothesis that continuously scanning for the camera and initializing it immediately upon connection enables stable camera operation.
