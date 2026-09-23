# 免费节点抓取 (Free Node Scraper)

一个通用的免费代理节点抓取与聚合工具，支持从公开订阅源抓取 `vmess`/`vless`/`trojan`/`ss`/`ssr` 节点，
去重后生成可供 Clash / V2Ray 等客户端使用的订阅文件。

> 本工具仅用于聚合公开、免费共享的代理节点信息，不包含任何绕过付费或商业服务的内容。
> 实际抓取效果取决于你提供的订阅源是否可用、合法。

## 功能

- 从多个订阅源 URL 抓取原始内容（自动识别 base64 编码或明文节点链接）
- 解析 `vmess://`、`vless://`、`trojan://`、`ss://`、`ssr://` 节点链接
- 按协议 + 服务器 + 端口 + 认证信息去重
- 输出：
  - `output/subscription.txt`：base64 编码的订阅文件，可直接导入客户端
  - `output/clash.yaml`：Clash 配置文件（包含 `proxies`、`proxy-groups`、`rules`）

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

1. 编辑 `sources.txt`，每行填写一个订阅源 URL（以 `#` 开头的行会被忽略）：

   ```
   https://example.com/free-nodes-1
   https://example.com/free-nodes-2
   ```

2. 运行抓取工具：

   ```bash
   python -m free_node_scraper.cli --sources sources.txt --output output
   ```

3. 生成的文件位于 `output/` 目录下：
   - `subscription.txt`
   - `clash.yaml`

### 命令行参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--sources` | 订阅源列表文件路径 | `sources.txt` |
| `--output` | 输出目录 | `output` |
| `--timeout` | 单个请求超时时间（秒） | `15` |
| `-v, --verbose` | 输出详细日志 | 关闭 |

## 运行测试

```bash
pip install -r requirements.txt pytest
python -m pytest
```

## 项目结构

```
free_node_scraper/
├── __init__.py
├── fetcher.py   # 抓取与 base64/明文解码
├── parsers.py   # 各协议节点链接解析
├── dedup.py     # 节点去重
├── writer.py    # 输出 subscription.txt / clash.yaml
└── cli.py       # 命令行入口
sources.txt      # 订阅源列表（示例/占位）
tests/           # 单元测试（使用本地样例数据，不依赖真实网络）
```