# 引擎与可改造边界

《Real Pool 3D》客户端（`Poolians.exe` 2.22.8.0，Steam AppID 670290）的构成：

| 层 | 实现 |
|---|---|
| 渲染 | **OGRE 1.8.1 "Byatis"**（`OgreMain.dll`，链接时间 2012-09-02，官方原版） |
| 后端 | `RenderSystem_Direct3D9.dll` / `RenderSystem_GL.dll`，默认 D3D9 固定管线 |
| 界面 | **Qt 4.8**，OGRE 渲染到 Qt 窗口（`externalWindowHandle`） |
| 玩法 | 自研 C++：`CBall` `CCue` `CAimSphere` `CRuleEight`…，物理与规则全在客户端 |
| 网络 | Boost.Asio + QtNetwork + ENet（UDP），协议为 `0x7D9/0x7DA/0x7DB/0x7DD/0x7DE` 状态消息 |
| 资源 | 自定义 `pak` 归档（XOR 0x78 的 ZIP），`resources.cfg` 描述挂载点 |

## 关键结论一：pak 恒定优先于 FileSystem

`resources.cfg` 长这样：

```
[Basic]
FileSystem=RealPool3D/common      ← 想用它覆盖贴图
pak=General/3d/all.pak
pak=RealPool3D/3d/common.pak
```

实测（放一张纯洋红贴图进 `common`，进游戏统计洋红像素）：**0 个**。
无论 `FileSystem` 放在 pak 前面还是后面，pak 里的同名文件都会赢。

结论：**贴图只能打进 pak**，`FileSystem` 目录只能提供 pak 里没有的文件。

## 关键结论二：材质脚本可以覆盖

把 `ball.material` 的 `diffuse` 改成纯绿，放进 `FileSystem` 目录 → 进游戏所有球变绿。

原因：OGRE 解析 `.material` 时会遍历**所有**归档，同名材质**后解析的覆盖先解析的**，
这与"资源查找优先级"是两套机制。所以：

- **材质** → `FileSystem` 目录覆盖即可（本项目仍选择写进 pak，省得用户改配置）
- **贴图** → 必须重打包

## 关键结论三：光影改不动

- `OgreMain.dll` 里 `RTShader` 命中 **0** 次 —— 这个 build 没编 RTShaderSystem，
  没法用 RTSS 自动生成法线贴图/逐像素光照。
- 程序从未调用 `setShadowTechnique`，只有自研的 `CSimpleShadow`（贴图假阴影，
  `Simple_Ball_Shadow1` + 一张 823 字节的 `ball_shadow1.png`）。
- 没有 Compositor 使用痕迹 → 加不了 Bloom / SSAO / 后处理管线。

所以仓库能做的"光影"只有两条：

1. 重制**烘焙光照贴图**（`room1.pak` 里的 `lightmap.jpg`，原版仅 320×320）
2. 把**假阴影贴图**放大柔化

想要实时效果的唯一现实路径是 **ReShade**（D3D9 注入，只作用于颜色域），见 `reshade/`。

## 其它可用信息

- 画质相关档位存在 `change/options.dat`：`Graphics Quality = Basic|Low|Medium|High`、
  `Ball Speed`、`Mouse Sensitivity`；外观在 `change/look.dat`（背景/桌布/亮度）。
- 界面素材有 **1K/2K/3K/4K 四套**（`gui/{1K,2K,3K,4K}`），由 `UI Scaling` 选项切换，
  4K 那套是官方用 Upscayl 超分出来的（包里还留着 `upscayl_png_ultramix-balanced-4x_2x/` 目录名）。
  想让界面变清晰，先把 `UI Scaling` 调到 200%，比替换任何素材都划算。
- 球的 3D 贴图是运行时按名字 `ball%d.bmp` 动态指给材质实例的，
  材质里写死的 `ball2.bmp` 只是占位。

## 未做的事（给后来者）

- `Pool2D` 的 pak（9 MB / 175 张图）没有处理。
- 球桌网格 `table1.mesh` 只有一张 1024 宽的台布，没有法线/高光贴图；
  加上法线贴图需要自写 HLSL，且网格大概率没有切线数据（老 OgreMax 导出默认不带）。
