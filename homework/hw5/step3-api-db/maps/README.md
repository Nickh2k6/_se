# maps/

各樓層地圖放這裡（Nav2 的 `.pgm` + `.yaml`），例如：

```
maps/
├── floor1.pgm
├── floor1.yaml
├── floor2.pgm
└── floor2.yaml
```

這個資料夾會掛載到容器內的 `/ws/maps`，主機和容器看到的是同一份檔案。
在容器內用 SLAM Toolbox 建好圖後存到 `/ws/maps`，主機上就會直接出現。
