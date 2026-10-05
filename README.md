# -

免费节点抓取聚合工具:抓取订阅 → 去重 → TCP 可用性检测(按延迟排序)→ 输出 Clash 配置。

```
python -m free_node_scraper.cli <订阅URL...> -o clash.yaml [--timeout 5] [--max-latency 800] [--no-check]
```
支持 ss / vmess / trojan / vless 链接(明文或 base64 订阅)。可用性检测仅为 TCP 连通,不保证节点真正可用。
