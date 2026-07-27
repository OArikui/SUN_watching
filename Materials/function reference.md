# 関数の説明

2026/07/26  
高校2年 島野淳

## RANSAC

version 1.00

### calculate_west_angle_robust

#### env

**`python`** v3.13.3

- **`typing`**

- **`numpy`**

- **`sklearn.linear_model`**

- **`math`**

#### argument

- **`p_lst`** :`Union[List[List[float]], NDArray[np.float64]]`   
  時系列順の軌跡の座標集合`[[x1,y1],[x2,y2]...]`の形式。最低長は2
  
  - 時間単位での速度ベクトルを生成するため、時系列順

- **`time_stomps`**:`Optional[Union[List[float], NDArray[np.float32]]] = None`   
  `p_lst`の各要素のタイムスタンプ
  
  - オプショナルの変数だが、時刻の推移を精細に追跡するためには必須
  
  - `p_lst`と長さが一致する必要がある
  
  > [!WARNING]
  > `p_lst`と長さが一致しないまたは`time_stomp=None`場合は`time_stomp`は無視され、等間隔のタイムスタンプによるベクトル推定を行う

#### return

- `Optional[Tuple[float, Tuple[float, float]]]`  
  推定結果`(angle_deg,(vx,vy))`の形式
  
  - `angle_deg`:`p_lst`座標の移動方向`float`  
    座標系:右が0°,真上が90°,左180°,真下270°のデカルト座標系  
    値域:`-180~180` \*右向きは180°なので-180より大きい範囲  
    単位:degree
  
  - `vx`:単位時間当たりのx方向移動量  
    座標系:`p_lst`,`timestomp`の座標系に依存  
    単位:`p_lstの単位/timestompの単位`
  
  - `vy`:単位時間当たりのy方向移動量  
    座標系:`p_lst`,`timestomp`の座標系に依存  
  
      　単位:`p_lstの単位/timestompの単位`

#### raise

- `if len(p_lst) < 2`ベクトル推定には最低でも2つの点が必要

#### method

##### definition

- `x`:時系列順のx座標リスト

- `y`:時系列順のy座標リスト

- `t`:座標リストの各要素の時刻リスト

##### flow

1. `p_lst`から各軸座標を抽出し、`x`,`y`を作成

2. `time_stomp`を`t`にリネーム.`time_stomp`がNoneもしくは`p_lst`に対応しなければ生成

3. `RANSAC.RANSACRegressor`に`t`をもちいてx速度とy速度を推定し,`vx`と`vy`を作成

4. `math.atan2`を用いて,`vx`と`vy`からradiansの移動方向を計算

5. `math.degrees`を用いてradiansからdegreesに変換し、移動方向の角度を算出

#### process

```python
    points = np.asarray(p_lst, dtype=np.float64)

    # 角度計算には最低2点が必要
    if len(points) < 2:
        raise ("_____")

    # 時間インデックス t の作成と2次元配列化 (n_samples, 1)
    if time_stomps is None or len(time_stomps) != len(points):
        t: NDArray[np.float64] = np.arange(len(points), dtype=np.float64).reshape(-1, 1)
    else:
        t = np.asarray(time_stomps, dtype=np.float64).reshape(-1, 1)

    # x座標とy座標の分離
    x: NDArray[np.float64] = points[:, 0]
    y: NDArray[np.float64] = points[:, 1]

    # x方向の速度(傾き)をRANSACで推定
    ransac_x = RANSACRegressor(random_state=42)
    ransac_x.fit(t, x)
    # estimator_ は学習済みの LinearRegression インスタンス
    vx: float = float(ransac_x.estimator_.coef_[0])

    # y方向の速度(傾き)をRANSACで推定
    ransac_y = RANSACRegressor(random_state=42)
    ransac_y.fit(t, y)
    vy: float = float(ransac_y.estimator_.coef_[0])

    # ベクトルからラジアン・度数法へ変換
    angle_rad: float = math.atan2(vy, vx)
    angle_deg: float = math.degrees(angle_rad)

    return angle_deg, (vy, vx)
```
