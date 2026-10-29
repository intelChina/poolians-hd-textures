# `.pak` 格式

结论一句话：**`<file>.pak` 就是一个普通 ZIP，整份文件逐字节异或了 `0x78`。**

## 证据

`RealPool3D/3d/common.pak` 前 10 字节：

```
28 33 7B 7C 6C 78 78 78 70 78
```

逐字节 XOR `0x78`：

```
50 4B 03 04 14 00 00 00 08 00   ->  "PK\x03\x04"  版本 2.0，method=8 (deflate)
```

异或后的缓冲区可以直接交给 `zipfile` / `unzip`，条目名、压缩方式、时间戳全部正常：

```
$ python tools/pakcodec.py common.pak -l
ball0.bmp                     49206 ->    49206
ball1.bmp                     49208 ->    49208
zm.jpg                       148865 ->   148680
ball.material                  2891 ->     2891
...
132 entries, 2.9 MB unpacked
```

游戏日志里也能看到自注册的归档类型：

```
22:48:10: ArchiveFactory for archive type pak registered.
```

## 这不是 OGRE 自带的格式

OGRE 只自带 `FileSystem` 和 `Zip` 两种归档。日志里 `pak` 是游戏自己注册的 `ArchiveFactory`，
实现方式就是"读文件 → 异或 → 当 ZIP 解析"。没有加密、没有压缩字典、没有校验，
异或密钥对全部 4 个 pak（以及 `Pool2D` 的）都是 `0x78`。

## 写回

`encode()` 是同一个操作（XOR 是对合的），所以重建 pak 就是：

1. 读出 `.pak`，XOR `0x78` → ZIP
2. 用 `zipfile` 解出条目、替换要改的文件
3. 重新打 ZIP（保持条目顺序、时间戳、属性，保证可复现）
4. 整份 XOR `0x78` → 写回 `.pak`

`tools/pakcodec.py` 里的 `open_pak()` / `repack()` 就是这两步。

## 体积参考

| pak | 原版 | 替换贴图后 |
|---|---|---|
| `RealPool3D/3d/common.pak` | 1.7 MB | 15.2 MB |
| `RealPool3D/3d/room1.pak` | 0.5 MB | 3.5 MB |
| `RealSnooker3D/3d/common.pak` | 2.3 MB | 13.5 MB |
| `RealSnooker3D/3d/room1.pak` | 0.5 MB | 3.5 MB |

## 注意

- 游戏启动时会用 `general/change/vs.dat` 里的哈希和服务器比对资源包，**官方更新会覆盖修改过的 pak**。
  备份后缀用 `.backup` / `.dsh_backup` / `.orig` 之类的名字，`build.py` 会自动识别。
- 3D 场景贴图只在 pak 里，用 `FileSystem` 目录覆盖同名文件是**无效**的（见 `engine-notes.md`）。
