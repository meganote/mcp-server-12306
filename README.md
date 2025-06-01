# 🚄 12306 MCP Server

![screenshot](https://img.shields.io/badge/12306-MCP-blue?logo=railway) ![FastAPI](https://img.shields.io/badge/FastAPI-async-green?logo=fastapi) ![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)

---

## ✨ 项目简介

12306 MCP Server 是一款基于 Model Context Protocol (MCP) 的高性能火车票查询后端，支持官方 12306 余票、车站、经停、换乘等多种查询，适配 AI/自动化/智能助手等场景。界面友好，易于集成，开箱即用。

---

## 🚀 功能亮点

- 实时余票/车次/座席/时刻/换乘一站式查询
- 全国车站信息管理与模糊搜索
- 官方经停站、一次中转方案全支持
- SSE流式协议，AI/前端无缝对接
- FastAPI异步高性能，秒级响应
- MCP标准，AI/自动化场景即插即用

---

## 🛠️ 快速上手

### 环境要求
- Python 3.10+
- [uv](https://astral.sh/uv/)（推荐包管理器）

### 本地一键部署
```bash
# 克隆项目
git clone https://github.com/drfccv/12306-mcp-server.git
cd 12306-mcp-server

# 安装依赖
uv sync

# 更新车站信息（必须先执行）
uv run python scripts/update_stations.py

# 启动服务器
uv run python scripts/start_server.py
```

### Docker 部署
```bash
# 直接拉取已构建镜像
 docker pull drfccv/12306-mcp-server:latest

# 运行容器（映射8000端口）
 docker run -d -p 8000:8000 --name 12306-mcp-server drfccv/12306-mcp-server:latest
```

> 如需自定义开发或本地修改后再打包，可用如下命令自行构建镜像：
> ```bash
> docker build -t drfccv/12306-mcp-server:latest .
> ```

### 配置
复制 `.env.example` 为 `.env` 并按需修改：
```bash
cp .env.example .env
```

---

## 🤖 API & 工具一览

### MCP 客户端配置示例
```json
{
  "mcpServers": {
    "12306": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

### 支持的主流程工具
| 工具名                    | 典型场景/功能描述                 |
|--------------------------|----------------------------------|
| query_tickets            | 余票/车次/座席/时刻一站式查询     |
| search_stations          | 车站模糊搜索，支持中文/拼音/简拼   |
| get_station_info         | 获取车站详情（名称、代码、地理等） |
| query_transfer           | 一次中转换乘方案，自动拼接最优中转 |
| get_train_route_stations | 查询指定列车经停站及时刻表         |

---

## 📚 工具文档

本项目所有主流程工具的详细功能、实现与使用方法，均已收录于 [`/doc`](./doc) 目录下：

- [query_tickets.md](./doc/query_tickets.md) — 余票/车次/座席/时刻一站式查询
- [search_stations.md](./doc/search_stations.md) — 车站模糊搜索
- [get_station_info.md](./doc/get_station_info.md) — 获取车站详情
- [query_transfer.md](./doc/query_transfer.md) — 一次中转换乘方案
- [get_train_route_stations.md](./doc/get_train_route_stations.md) — 查询列车经停站

每个文档包含：
- 工具功能说明
- 实现方法
- 请求参数与返回示例
- 典型调用方式

如需二次开发或集成，建议先阅读对应工具的文档。

---

## 🧩 目录结构

```
src/mcp_12306/    # 主源代码
  ├─ server.py    # FastAPI主入口
  ├─ services/    # 业务逻辑（车票/车站/HTTP）
  ├─ models/      # 数据模型
  ├─ utils/       # 工具与配置
scripts/          # 启动与数据脚本
```

---

## 🧪 测试
```bash
uv run pytest
```

---

## 📦 镜像发布与拉取

- 镜像仓库：[drfccv/12306-mcp-server](https://hub.docker.com/r/drfccv/12306-mcp-server)
- 拉取镜像：
  ```bash
  docker pull drfccv/12306-mcp-server:latest
  ```
- 运行镜像：
  ```bash
  docker run -d -p 8000:8000 --name 12306-mcp-server drfccv/12306-mcp-server:latest
  ```

---

## 📄 License
MIT License

---

## ⚠️ 免责声明

- 本项目仅供学习、研究与技术交流，严禁用于任何商业用途。
- 本项目不存储、不篡改、不传播任何 12306 官方数据，仅作为官方公开接口的智能聚合与转发。
- 使用本项目造成的任何后果（包括但不限于账号封禁、数据异常、法律风险等）均由使用者本人承担，项目作者不承担任何责任。
- 请遵守中国法律法规及 12306 官方相关规定，合理合规使用。

---


