# ReShade 预设（可选）

这个预设只做**颜色域**的后处理，不碰引擎：

| 效果 | 作用 |
|---|---|
| `Deband.fx` | 去掉台布、墙纸上的 8-bit 色带 |
| `AdaptiveSharpen.fx` | 锐化，弥补贴图本身的柔度 |
| `Colourfulness.fx` | 轻微提升饱和度 |

## 安装

1. 从 <https://reshade.me> 下载 **5.4.x**（这个版本与经典效果包兼容性最好；
   6.x 对老 `technique` 语法支持变差）。
2. 安装时选游戏目录里的 `Poolians.exe`，渲染 API 选 **Direct3D 9**，
   效果包勾选 **Legacy standard effects**。
3. 把本目录的 `PooliansHQ.ini` 放到游戏根目录（和 `Poolians.exe` 同级）。
4. 游戏内按 `Home` 打开面板，在顶部下拉框里选 `PooliansHQ`。

## 说明

- 依赖 `ReShade.fxh` / `ReShadeUI.fxh` 等头文件，安装器会一起放好。
  如果你只拷了 `.fx` 没拷 `.fxh`，会出现 `could not open included file 'ReShade.fxh'`。
- **MXAO / SSAO 这类需要深度缓冲的效果在 D3D9 下大概率拿不到正确深度**，预设里没有启用。
- 试过加 `MagicBloom`，台布会过曝发白、影响看球，所以去掉了。想要发光感可以自己在面板里勾上。
- 不想要了就删掉游戏目录里的 `d3d9.dll`，游戏立刻回到原生渲染。
