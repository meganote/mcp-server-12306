import asyncio
import json
import logging
import random
from datetime import datetime, date
import datetime as dtmod

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .models.ticket import TicketQuery
from .services.station_service import StationService
from .services.ticket_service import TicketService
from .utils.config import get_settings
from .utils.date_utils import validate_date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()
station_service = StationService()
ticket_service = TicketService()

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

MCP_TOOLS = [
    {
        "name": "query_tickets",
        "description": "官方12306余票/车次/座席/时刻一站式查询。输入出发站、到达站、日期，返回所有可购车次、时刻、历时、各席别余票等详细信息。支持中文名、三字码。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "车票查询参数",
            "description": "查询火车票所需的参数",
            "properties": {
                "from_station": {
                    "type": "string",
                    "title": "出发站",
                    "description": "出发车站名称，例如：北京、上海、广州",
                    "minLength": 1
                },
                "to_station": {
                    "type": "string",
                    "title": "到达站",
                    "description": "到达车站名称，例如：北京、上海、广州",
                    "minLength": 1
                },
                "train_date": {
                    "type": "string",
                    "title": "出发日期",
                    "description": "出发日期，格式：YYYY-MM-DD",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                }
            },
            "required": ["from_station", "to_station", "train_date"],
            "additionalProperties": False
        }
    },
    {
        "name": "search_stations",
        "description": "智能模糊查站，支持中文名、拼音、简拼、三字码等多种方式，快速获取车站全名与三字码。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "车站搜索参数",
            "description": "搜索火车站所需的参数",
            "properties": {
                "query": {
                    "type": "string",
                    "title": "搜索关键词",
                    "description": "车站搜索关键词，支持：车站名称、拼音、简拼等",
                    "minLength": 1,
                    "maxLength": 20
                },
                "limit": {
                    "type": "integer",
                    "title": "结果数量限制",
                    "description": "返回结果的最大数量",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    {
        "name": "query_transfer",
        "description": "官方中转换乘方案查询。输入出发站、到达站、日期，可选中转站/无座/学生票，自动分页抓取全部中转方案，输出每段车次、时刻、余票、等候时间、总历时等详细信息。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "中转查询参数",
            "description": "查询A到B的中转换乘（含一次换乘）",
            "properties": {
                "from_station": {
                    "type": "string",
                    "title": "出发站"
                },
                "to_station": {
                    "type": "string",
                    "title": "到达站"
                },
                "train_date": {
                    "type": "string",
                    "title": "出发日期",
                    "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                },
                "middle_station": {
                    "type": "string",
                    "title": "中转站（可选）",
                    "description": "指定中转站名称或三字码，可选"
                },
                "isShowWZ": {
                    "type": "string",
                    "title": "是否显示无座车次（Y/N）",
                    "description": "Y=显示无座车次，N=不显示，默认N",
                    "default": "N"
                },
                "purpose_codes": {
                    "type": "string",
                    "title": "乘客类型（00=普通，0X=学生）",
                    "description": "00为普通，0X为学生，默认00",
                    "default": "00"
                }
            },
            "required": ["from_station", "to_station", "train_date"],
            "additionalProperties": False
        }
    },
    {
        "name": "get-train-route-stations",
        "description": "列车经停站全表查询。支持输入车次号或官方编号，自动转换，返回所有经停站、到发时刻、停留时间。支持三字码/全名。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "列车经停站查询参数",
            "properties": {
                "train_no": {"type": "string", "title": "车次编码", "minLength": 1},
                "from_station": {"type": "string", "title": "出发站id", "minLength": 1},
                "to_station": {"type": "string", "title": "到达站id", "minLength": 1},
                "train_date": {"type": "string", "title": "出发日期", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}
            },
            "required": ["train_no", "from_station", "to_station", "train_date"],
            "additionalProperties": False
        }
    },
    {
        "name": "get-train-no-by-train-code",
        "description": "车次号转官方唯一编号（train_no），支持三字码/全名。常用于经停站查询前置转换。",
        "inputSchema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "车次号转编号参数",
            "properties": {
                "train_code": {"type": "string", "title": "车次号", "minLength": 1},
                "from_station": {"type": "string", "title": "出发站id或全名", "minLength": 1},
                "to_station": {"type": "string", "title": "到达站id或全名", "minLength": 1},
                "train_date": {"type": "string", "title": "出发日期", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}
            },
            "required": ["train_code", "from_station", "to_station", "train_date"],
            "additionalProperties": False
        }
    }
]

app = FastAPI(
    title="12306 MCP Server",
    version="1.0.0",
    description="基于MCP协议的12306火车票查询服务，支持直达、过站和换乘查询"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
async def root():
    return {
        "name": "12306 MCP Server",
        "version": "1.0.0",
        "status": "running",
        "mcp_endpoint": "/sse",
        "stations_loaded": len(station_service.stations),
        "tools": [tool["name"] for tool in MCP_TOOLS]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "stations": len(station_service.stations)
    }

@app.get("/schema/tools")
async def get_tools_schema():
    return {
        "tools": MCP_TOOLS,
        "schema_version": "http://json-schema.org/draft-07/schema#"
    }

@app.options("/sse")
async def sse_options():
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.get("/sse")
async def sse_endpoint():
    logger.info("🔗 新的SSE连接建立")
    async def generate_events():
        try:
            server_info = {
                "jsonrpc": "2.0",
                "method": "server/info",
                "params": {
                    "serverInfo": {
                        "name": "12306-mcp",
                        "version": "1.0.0",
                        "description": "12306火车票查询服务"
                    },
                    "capabilities": {
                        "tools": {
                            "list": True,
                            "call": True
                        }
                    },
                    "protocolVersion": "2024-11-05"
                }
            }
            yield f"data: {json.dumps(server_info, ensure_ascii=False)}\n\n"
            logger.info("📤 发送服务器信息")
            await asyncio.sleep(0.2)

            tools_list = {
                "jsonrpc": "2.0",
                "method": "tools/list_changed",
                "params": {
                    "tools": MCP_TOOLS
                }
            }
            yield f"data: {json.dumps(tools_list, ensure_ascii=False)}\n\n"
            logger.info(f"📤 发送工具列表 - {len(MCP_TOOLS)} 个工具")
            await asyncio.sleep(0.2)

            initialized = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {
                    "ready": True,
                    "toolsCount": len(MCP_TOOLS),
                    "stationsLoaded": len(station_service.stations),
                    "timestamp": datetime.now().isoformat()
                }
            }
            yield f"data: {json.dumps(initialized, ensure_ascii=False)}\n\n"
            logger.info("✅ MCP握手完成!")
            await asyncio.sleep(0.2)

            welcome = {
                "jsonrpc": "2.0",
                "method": "notifications/message",
                "params": {
                    "type": "info",
                    "title": "🚄 12306车票查询服务已就绪",
                    "message": "可用工具:\n• query_tickets - 查询火车票\n• search_stations - 搜索车站\n• query_transfer - 中转换乘查询",
                    "examples": [
                        "中转查询: @12306 query_transfer from_station=北京 to_station=昆明 train_date=2025-06-01"
                    ]
                }
            }
            yield f"data: {json.dumps(welcome, ensure_ascii=False)}\n\n"
            logger.info("🎉 发送欢迎消息")

            counter = 0
            while True:
                counter += 1
                heartbeat = {
                    "jsonrpc": "2.0",
                    "method": "notifications/heartbeat",
                    "params": {
                        "counter": counter,
                        "timestamp": datetime.now().isoformat(),
                        "status": "ready",
                        "stationsLoaded": len(station_service.stations)
                    }
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            logger.info("🔌 SSE连接已断开")
        except Exception as e:
            logger.error(f"❌ SSE流错误: {e}")
            error_event = {
                "jsonrpc": "2.0",
                "method": "notifications/error",
                "params": {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.post("/sse")
async def sse_post(request: Request):
    data = None
    try:
        data = await request.json()
        method = data.get("method", "unknown")
        params = data.get("params", {})
        req_id = data.get("id")
        logger.info(f"📨 收到RPC调用: {method}")

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            logger.info(f"🔧 执行工具: {tool_name}")
            logger.info(f"📋 参数: {arguments}")
            if tool_name == "query_tickets":
                content = await query_tickets_validated(arguments)
            elif tool_name == "search_stations":
                content = await search_stations_validated(arguments)
            elif tool_name == "query_transfer":
                content = await query_transfer_validated(arguments)
            elif tool_name == "get-train-route-stations":
                content = await get_train_route_stations_validated(arguments)
            elif tool_name == "get-train-no-by-train-code":
                content = await get_train_no_by_train_code_validated(arguments)
            else:
                content = [{"type": "text", "text": f"❌ 未知工具: {tool_name}"}]
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": content
                }
            }
            logger.info(f"✅ 工具 {tool_name} 执行完成")
        elif method == "tools/list":
            logger.info("📋 返回工具列表")
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": MCP_TOOLS
                }
            }
        elif method == "initialize":
            logger.info("🚀 处理初始化请求")
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "serverInfo": {
                        "name": "12306-mcp",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {
                            "list": True,
                            "call": True
                        }
                    },
                    "protocolVersion": "2024-11-05"
                }
            }
        elif method.startswith("notifications/"):
            notification_type = method.replace("notifications/", "")
            logger.info(f"📢 收到通知: {notification_type}")
            return JSONResponse({
                "status": "acknowledged",
                "notification": notification_type
            })
        else:
            logger.warning(f"⚠️  未知方法: {method}")
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"方法未找到: {method}"
                }
            }
        return JSONResponse(response)
    except Exception as e:
        logger.error(f"❌ 处理RPC请求失败: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": data.get("id") if data else None,
            "error": {
                "code": -32603,
                "message": f"内部错误: {str(e)}"
            }
        }, status_code=500)

def parse_ticket_string(ticket_str, query):
    parts = ticket_str.split('|')
    if len(parts) < 35:
        return None
    return {
        "train_no": parts[3],
        "start_time": parts[8],
        "arrive_time": parts[9],
        "duration": parts[10],
        "business_seat_num": parts[32] or "",
        "first_class_num": parts[31] or "",
        "second_class_num": parts[30] or "",
        "advanced_soft_sleeper_num": parts[21] or "",
        "soft_sleeper_num": parts[23] or "",
        "dongwo_num": parts[33] or "",
        "hard_sleeper_num": parts[28] or "",
        "soft_seat_num": parts[24] or "",
        "hard_seat_num": parts[29] or "",
        "no_seat_num": parts[26] or "",
        "from_station": query["from_station"],
        "to_station": query["to_station"],
        "train_date": query["train_date"]
    }

async def query_tickets_validated(args: dict) -> list:
    try:
        from_station = args.get("from_station", "").strip()
        to_station = args.get("to_station", "").strip()
        train_date = args.get("train_date", "").strip()
        logger.info(f"🔍 查询参数: {from_station} → {to_station} ({train_date})")

        errors = []
        if not from_station:
            errors.append("出发站不能为空")
        if not to_station:
            errors.append("到达站不能为空")
        if not train_date:
            errors.append("出发日期不能为空")
        elif not validate_date(train_date):
            errors.append("日期格式错误，请使用 YYYY-MM-DD 格式")
        if errors:
            error_text = "❌ **参数验证失败:**\n" + "\n".join(f"{i+1}. {err}" for i, err in enumerate(errors))
            return [{"type": "text", "text": error_text}]

        from_code, to_code = None, None
        from_station_obj = await station_service.get_station_by_name(from_station)
        to_station_obj = await station_service.get_station_by_name(to_station)
        if from_station_obj:
            from_code = from_station_obj.code
        if to_station_obj:
            to_code = to_station_obj.code
        if not from_code:
            result = await station_service.search_stations(from_station, 1)
            if result.stations:
                from_code = result.stations[0].code
        if not to_code:
            result = await station_service.search_stations(to_station, 1)
            if result.stations:
                to_code = result.stations[0].code
        if not from_code or not to_code:
            # 智能建议：自动模糊匹配并展示前3条建议
            suggest_text = ""
            if not from_code:
                result = await station_service.search_stations(from_station, 3)
                if result.stations:
                    suggest_text += f"\n\n🔍 出发站“{from_station}”可能是：\n"
                    for s in result.stations:
                        suggest_text += f"- {s.name}（{s.code}，拼音：{s.pinyin}，简拼：{s.py_short}）\n"
            if not to_code:
                result = await station_service.search_stations(to_station, 3)
                if result.stations:
                    suggest_text += f"\n\n🔍 到达站“{to_station}”可能是：\n"
                    for s in result.stations:
                        suggest_text += f"- {s.name}（{s.code}，拼音：{s.pinyin}，简拼：{s.py_short}）\n"
            return [{"type": "text", "text": "❌ 车站名称无效，请检查输入。" + suggest_text + "\n\n💡 可尝试拼音、简拼、三字码或用 search_stations 工具辅助查询。"}]

        async def get_12306_json(url, params=None, max_retry=3):
            headers = {
                "User-Agent": USER_AGENT,
                "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
                "Host": "kyfw.12306.cn",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }
            for retry in range(max_retry):
                async with httpx.AsyncClient(follow_redirects=True, timeout=8, verify=False) as client:
                    resp = await client.get("https://kyfw.12306.cn/otn/leftTicket/init", headers=headers)
                    cookies = resp.cookies
                    await asyncio.sleep(random.uniform(0.6, 1.2))
                    resp = await client.get(url, headers=headers, params=params, cookies=cookies)
                    if "error.html" in str(resp.url):
                        if retry < max_retry - 1:
                            logger.warning(f"12306反爬虫触发，正在第{retry+1}次重试...")
                            await asyncio.sleep(random.uniform(1.0, 3.0))
                            continue
                        else:
                            raise Exception("12306反爬虫触发，被重定向到error.html")
                    return resp.json()
            raise Exception("尝试多次后仍被12306限制，请稍后再试。")

        url = "https://kyfw.12306.cn/otn/leftTicket/query"
        params = {
            "leftTicketDTO.train_date": train_date,
            "leftTicketDTO.from_station": from_code,
            "leftTicketDTO.to_station": to_code,
            "purpose_codes": "ADULT"
        }
        try:
            resp_json = await get_12306_json(url, params)
            data = resp_json.get("data", {})
            tickets_data = data.get("result", [])
            tickets = []
            for ticket_str in tickets_data:
                ticket = parse_ticket_string(ticket_str, {
                    "from_station": from_station,
                    "to_station": to_station,
                    "train_date": train_date
                })
                if ticket:
                    tickets.append(ticket)
            if tickets:
                text = f"🚄 **{from_station} → {to_station}** ({train_date})\n\n"
                text += f"📊 找到 **{len(tickets)}** 趟列车:\n\n"
                for i, ticket in enumerate(tickets, 1):
                    # 解析真实出发站和到达站三字码及中文名
                    ticket_str = tickets_data[i-1] if i-1 < len(tickets_data) else None
                    from_station_name = to_station_name = from_code = to_code = None
                    if ticket_str:
                        parts = ticket_str.split('|')
                        from_code = parts[6] if len(parts) > 6 else None
                        to_code = parts[7] if len(parts) > 7 else None
                        from_station_obj = await station_service.get_station_by_code(from_code) if from_code else None
                        to_station_obj = await station_service.get_station_by_code(to_code) if to_code else None
                        from_station_name = from_station_obj.name if from_station_obj else (from_code or "?")
                        to_station_name = to_station_obj.name if to_station_obj else (to_code or "?")
                    # 输出格式：车次（出发站[三字码]→到达站[三字码]）
                    text += f"**{i}.** 🚆 **{ticket['train_no']}** （{from_station_name}[{from_code}] → {to_station_name}[{to_code}]）\n"
                    text += f"      ⏰ `{ticket['start_time']}` → `{ticket['arrive_time']}`"
                    if ticket['duration']:
                        text += f" (历时 {ticket['duration']})"
                    text += "\n"
                    seats = []
                    if ticket['business_seat_num']: seats.append(f"商务座:{ticket['business_seat_num']}")
                    if ticket['first_class_num']: seats.append(f"一等座:{ticket['first_class_num']}")
                    if ticket['second_class_num']: seats.append(f"二等座:{ticket['second_class_num']}")
                    if ticket['advanced_soft_sleeper_num']: seats.append(f"高级软卧:{ticket['advanced_soft_sleeper_num']}")
                    if ticket['soft_sleeper_num']: seats.append(f"软卧:{ticket['soft_sleeper_num']}")
                    if ticket['hard_sleeper_num']: seats.append(f"硬卧:{ticket['hard_sleeper_num']}")
                    if ticket['soft_seat_num']: seats.append(f"软座:{ticket['soft_seat_num']}")
                    if ticket['hard_seat_num']: seats.append(f"硬座:{ticket['hard_seat_num']}")
                    if ticket['no_seat_num']: seats.append(f"无座:{ticket['no_seat_num']}")
                    if ticket['dongwo_num']: seats.append(f"动卧:{ticket['dongwo_num']}")
                    if seats:
                        text += f"      💺 {' | '.join(seats)}\n"
                    text += "\n"
                return [{"type": "text", "text": text}]
            else:
                return [{"type": "text", "text": f"❌ 未找到该线路的余票（{from_station}→{to_station} {train_date}）"}]
        except Exception as e:
            logger.warning(str(e))
            return [{"type": "text", "text": f"⚠️ 查询被12306频率限制，请稍后再试或访问12306官网。\n\n详细：{e}"}]
    except Exception as e:
        logger.error(f"❌ 查询车票失败: {e}")
        return [{"type": "text", "text": f"❌ **查询失败:** {str(e)}"}]

async def search_stations_validated(args: dict) -> list:
    try:
        query = args.get("query", "").strip()
        limit = args.get("limit", 10)
        if not query:
            return [{"type": "text", "text": "❌ 请输入搜索关键词"}]
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            limit = 10
        result = await station_service.search_stations(query, limit)
        if result.stations:
            text = f"🚉 **搜索结果:** `{query}`\n\n"
            text += f"📊 找到 **{len(result.stations)}** 个车站:\n\n"
            for i, station in enumerate(result.stations, 1):
                text += f"**{i}.** 🚉 **{station.name}** `({station.code})`\n"
                text += f"       📍 拼音: `{station.pinyin}`"
                if station.py_short:
                    text += f" | 简拼: `{station.py_short}`"
                text += "\n"
                if hasattr(station, 'num') and station.num:
                    text += f"       🔢 编号: `{station.num}`\n"
                text += "\n"
            return [{"type": "text", "text": text}]
        else:
            text = f"❌ **未找到匹配的车站**\n\n"
            text += f"🔍 **搜索关键词:** `{query}`\n\n"
            text += f"💡 **搜索建议:**\n"
            text += f"• 尝试完整城市名称 (如: `北京`)\n"
            text += f"• 尝试拼音 (如: `beijing`)\n"
            text += f"• 尝试简拼 (如: `bj`)\n"
            text += f"• 检查拼写是否正确"
            return [{"type": "text", "text": text}]
    except Exception as e:
        logger.error(f"❌ 搜索车站失败: {e}")
        return [{"type": "text", "text": f"❌ **搜索失败:** {str(e)}"}]

# --- 优化 query_transfer_validated 输出 ---
async def query_transfer_validated(args: dict) -> list:
    from_station = args.get("from_station", "").strip()
    to_station = args.get("to_station", "").strip()
    train_date = args.get("train_date", "").strip()
    middle_station = args.get("middle_station", "").strip() if "middle_station" in args else ""
    isShowWZ = args.get("isShowWZ", "N").strip().upper() or "N"
    purpose_codes = args.get("purpose_codes", "00").strip().upper() or "00"
    if not from_station or not to_station or not train_date:
        return [{"type": "text", "text": "❌ 请输入出发站、到达站和出发日期"}]
    # 自动转三字码
    async def ensure_telecode(val):
        if val.isalpha() and val.isupper() and len(val) == 3:
            return val
        code = await station_service.get_station_code(val)
        return code
    from_code = await ensure_telecode(from_station)
    to_code = await ensure_telecode(to_station)
    if not from_code:
        return [{"type": "text", "text": f"❌ 出发站无效或无法识别：{from_station}"}]
    if not to_code:
        return [{"type": "text", "text": f"❌ 到达站无效或无法识别：{to_station}"}]
    import httpx
    url_init = "https://kyfw.12306.cn/otn/leftTicket/init"
    url = "https://kyfw.12306.cn/lcquery/queryU"
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Host": "kyfw.12306.cn",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://kyfw.12306.cn"
    }
    all_transfer_list = []
    async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
        await client.get(url_init, headers=headers)
        page_size = 10
        result_index = 0
        while True:
            params = {
                "train_date": train_date,
                "from_station_telecode": from_code,
                "to_station_telecode": to_code,
                "middle_station": middle_station,
                "result_index": str(result_index),
                "can_query": "Y",
                "isShowWZ": isShowWZ,
                "purpose_codes": purpose_codes,
                "channel": "E"
            }
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 302 or "error.html" in str(resp.headers.get("location", "")):
                return [{"type": "text", "text": "❌ 12306反爬虫拦截（302跳转），请稍后重试或更换网络环境。"}]
            try:
                data = resp.json().get("data", {})
                transfer_list = data.get("middleList", [])
            except Exception:
                return [{"type": "text", "text": "❌ 12306反爬拦截或数据异常，请稍后重试"}]
            if not transfer_list:
                break
            all_transfer_list.extend(transfer_list)
            if len(transfer_list) < page_size:
                break
            result_index += page_size
    if not all_transfer_list:
        return [{"type": "text", "text": f"❌ 未查到中转方案（{from_station}→{to_station} {train_date}）"}]
    text = f"🚉 **中转查询结果**\n\n{from_station} → {to_station}（{train_date}）\n\n"
    for i, item in enumerate(all_transfer_list, 1):
        try:
            # 优先用 fullList，降级用 trainList
            full_list = item.get("fullList") or item.get("trainList") or []
            if len(full_list) < 2:
                continue
            seg_texts = []
            for idx, seg in enumerate(full_list, 1):
                code = seg.get("station_train_code", "?")
                from_name = seg.get("from_station_name", "?")
                to_name = seg.get("to_station_name", "?")
                st = seg.get("start_time", "?")
                at = seg.get("arrive_time", "?")
                lishi = seg.get("lishi", "")
                # 余票字段严格按官方顺序输出
                seat_info = []
                # 商务座
                if "swz_num" in seg:
                    seat_info.append(f"商务座:{seg.get('swz_num', '--')}")
                # 特等座
                if "tz_num" in seg:
                    seat_info.append(f"特等座:{seg.get('tz_num', '--')}")
                # 一等座
                if "zy_num" in seg:
                    seat_info.append(f"一等座:{seg.get('zy_num', '--')}")
                # 二等座
                if "ze_num" in seg:
                    seat_info.append(f"二等座:{seg.get('ze_num', '--')}")
                # 高级软卧
                if "gr_num" in seg:
                    seat_info.append(f"高级软卧:{seg.get('gr_num', '--')}")
                # 软卧/动卧
                if "rw_num" in seg:
                    seat_info.append(f"软卧/动卧:{seg.get('rw_num', '--')}")
                # 一等卧
                if "rz_num" in seg:
                    seat_info.append(f"一等卧/软座:{seg.get('rz_num', '--')}")
                # 硬卧
                if "yw_num" in seg:
                    seat_info.append(f"硬卧:{seg.get('yw_num', '--')}")
                # 硬座
                if "yz_num" in seg:
                    seat_info.append(f"硬座:{seg.get('yz_num', '--')}")
                # 无座
                if "wz_num" in seg:
                    seat_info.append(f"无座:{seg.get('wz_num', '--')}")
                seg_text = f"    {idx}. {code} {from_name}({st}) → {to_name}({at})"
                if lishi:
                    seg_text += f" 历时:{lishi}"
                if seat_info:
                    seg_text += "\n         " + " | ".join(seat_info)
                seg_texts.append(seg_text)
            mid_station = item.get("middle_station_name") or full_list[0].get("to_station_name", "?")
            wait_time = item.get("wait_time", "")
            all_lishi = item.get("all_lishi", "")
            text += f"**{i}.** 中转站:{mid_station}  ⏱️总历时:{all_lishi}  ⏳等候:{wait_time}\n"
            text += "\n".join(seg_texts) + "\n\n"
        except Exception as e:
            text += f"**{i}.** [解析失败] {e}\n"
            continue
    return [
        {"type": "text", "text": text},
        {"type": "json", "json": all_transfer_list}
    ]

async def get_train_route_stations_validated(args: dict) -> list:
    train_no = args.get("train_no", "").strip()
    from_station = args.get("from_station", "").strip()
    to_station = args.get("to_station", "").strip()
    train_date = args.get("train_date", "").strip()
    # 日期校验
    try:
        dt = datetime.strptime(train_date, "%Y-%m-%d")
        if dt.date() < date.today():
            return [{"type": "text", "text": "❌ 出发日期不能早于今天"}]
    except Exception:
        return [{"type": "text", "text": "❌ 出发日期格式错误，应为YYYY-MM-DD"}]

    # --- 新增：支持车次号自动转编号 ---
    def is_train_no(val):
        # 12306编号一般为数字+大写字母+数字，长度>8
        return len(val) > 8 and any(c.isdigit() for c in val) and any(c.isalpha() for c in val)
    orig_train_code = train_no  # 保存原始车次号
    if not is_train_no(train_no):
        # 认为是车次号，自动查编号
        args_no = {
            "train_code": train_no,
            "from_station": from_station,
            "to_station": to_station,
            "train_date": train_date
        }
        res = await get_train_no_by_train_code_validated(args_no)
        if res and res[0].get("type") == "json" and res[0]["json"].get("train_no"):
            train_no = res[0]["json"]["train_no"]
        else:
            return res
    else:
        orig_train_code = args.get("train_code", train_no)  # 若本身就是编号，尝试用 train_code 字段

    # --- 新增：无论输入中文名还是三字码，均自动转为三字码 ---
    async def ensure_telecode(val):
        # 已是三字码直接返回，否则查code
        if val.isalpha() and val.isupper() and len(val) == 3:
            return val
        code = await station_service.get_station_code(val)
        return code
    from_station_code = await ensure_telecode(from_station)
    to_station_code = await ensure_telecode(to_station)
    if not from_station_code:
        return [{"type": "text", "text": f"❌ 出发站无效或无法识别：{from_station}"}]
    if not to_station_code:
        return [{"type": "text", "text": f"❌ 到达站无效或无法识别：{to_station}"}]

    # 车站id校验
    from_obj = await station_service.get_station_by_code(from_station_code)
    to_obj = await station_service.get_station_by_code(to_station_code)
    if not from_obj:
        return [{"type": "text", "text": f"❌ 出发站id无效: {from_station_code}"}]
    if not to_obj:
        return [{"type": "text", "text": f"❌ 到达站id无效: {to_station_code}"}]
    # 获取cookie并查询经停站，保持同一client实例
    import httpx
    url_init = "https://kyfw.12306.cn/otn/leftTicket/init"
    url = "https://kyfw.12306.cn/otn/czxx/queryByTrainNo"
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Host": "kyfw.12306.cn",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://kyfw.12306.cn"
    }
    async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
        # 先访问init获取cookie
        await client.get(url_init, headers=headers)
        params = {
            "train_no": train_no,
            "from_station_telecode": from_station_code,
            "to_station_telecode": to_station_code,
            "depart_date": train_date
        }
        resp = await client.get(url, headers=headers, params=params)
        # 检查是否被302跳转
        if resp.status_code == 302 or "error.html" in str(resp.headers.get("location", "")):
            return [{"type": "text", "text": "❌ 12306反爬虫拦截（302跳转），请稍后重试或更换网络环境。"}]
        data = resp.json().get("data", {})
        stations = data.get("data", [])
        # 兼容官方经停站接口返回的middleList结构（多段）
        if not stations and "middleList" in data:
            stations = []
            for m in data["middleList"]:
                if "fullList" in m:
                    stations.extend(m["fullList"])
        if not stations and "fullList" in data:
            stations = data["fullList"]
        if not stations and "route" in data:
            stations = data["route"]
    if not stations:
        return [{"type": "text", "text": "❌ 未查到该车次经停站信息"}]
    # 输出时显示原始车次号和编号
    text = f"🚄 **{orig_train_code}（编号: {train_no}）经停站信息**\n\n"
    for s in stations:
        arr = s.get("arrive_time", "----")
        dep = s.get("start_time", "----")
        stopover = s.get("stopover_time", "----")
        text += f"{s.get('from_station_no', s.get('station_no', '?'))}. {s.get('from_station_name', s.get('station_name', '?'))}  到达: {arr}  发车: {dep}  停留: {stopover}\n"
    return [{"type": "text", "text": text}]

async def get_train_no_by_train_code_validated(args: dict) -> list:
    """
    根据车次号、出发站、到达站、日期，查询唯一列车编号train_no。
    只允许精确匹配，所有参数必须为全名或三字码。
    自动兼容12306 /queryU 路径。
    """
    train_code = args.get("train_code", "").strip().upper()
    from_station = args.get("from_station", "").strip().upper()
    to_station = args.get("to_station", "").strip().upper()
    train_date = args.get("train_date", "").strip()
    try:
        dt = datetime.strptime(train_date, "%Y-%m-%d")
        if dt.date() < date.today():
            return [{"type": "text", "text": "❌ 出发日期不能早于今天"}]
    except Exception:
        return [{"type": "text", "text": "❌ 出发日期格式错误，应为YYYY-MM-DD"}]
    def is_telecode(val):
        return val.isalpha() and val.isupper() and len(val) == 3
    if not is_telecode(from_station):
        code = await station_service.get_station_code(from_station)
        if not code:
            return [{"type": "text", "text": f"❌ 出发站无效或无法识别：{from_station}"}]
        from_station = code
    if not is_telecode(to_station):
        code = await station_service.get_station_code(to_station)
        if not code:
            return [{"type": "text", "text": f"❌ 到达站无效或无法识别：{to_station}"}]
        to_station = code
    import httpx
    url_init = "https://kyfw.12306.cn/otn/leftTicket/init"
    url = "https://kyfw.12306.cn/otn/leftTicket/query"
    url_u = "https://kyfw.12306.cn/otn/leftTicket/queryU"
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        "Host": "kyfw.12306.cn",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }
    async with httpx.AsyncClient(follow_redirects=False, timeout=8, verify=False) as client:
        await client.get(url_init, headers=headers)
        params = {
            "leftTicketDTO.train_date": train_date,
            "leftTicketDTO.from_station": from_station,
            "leftTicketDTO.to_station": to_station,
            "purpose_codes": "ADULT"
        }
        resp = await client.get(url, headers=headers, params=params)
        # 302 跳转到 queryU
        if resp.status_code == 302 or resp.headers.get("location", "").endswith("queryU"):
            resp = await client.get(url_u, headers=headers, params=params)
        try:
            data = resp.json().get("data", {})
            tickets_data = data.get("result", [])
        except Exception:
            return [{"type": "text", "text": "❌ 12306反爬拦截或数据异常，请稍后重试"}]
    if not tickets_data:
        return [{"type": "text", "text": f"❌ 未找到该线路的余票数据（{from_station}->{to_station} {train_date}）"}]
    found = None
    for ticket_str in tickets_data:
        parts = ticket_str.split('|')
        try:
            idx = parts.index('预订')
            train_no = parts[idx+1].strip()
            train_code_str = parts[idx+2].strip().upper()
            if train_code_str == train_code:
                found = train_no
                break
        except Exception:
            continue
    if not found:
        debug_codes = []
        for p in tickets_data:
            try:
                parts = p.split('|')
                idx = parts.index('预订')
                debug_codes.append(parts[idx+2])
            except Exception:
                continue
        return [{"type": "text", "text": f"❌ 未找到该车次号的列车编号（{train_code} {from_station}->{to_station} {train_date}）。\n可用车次号: {debug_codes}"}]
    # 新增：兼容 Copilot/MCP 客户端，返回 type: text 结果
    return [
        {"type": "json", "json": {"train_code": train_code, "from_station": from_station, "to_station": to_station, "train_date": train_date, "train_no": found}},
        {"type": "text", "text": f"车次 {train_code}（{from_station}→{to_station}，{train_date}）的列车编号为：{found}"}
    ]

async def main_server():
    logger.info("🚂 加载车站数据...")
    await station_service.load_stations()
    logger.info(f"✅ 已加载 {len(station_service.stations)} 个车站")
    logger.info("🌐 启动HTTP/SSE服务器...")
    logger.info(f"📡 SSE端点: http://localhost:8000/sse")
    logger.info(f"📚 健康检查: http://localhost:8000/health")
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()

def main():
    asyncio.run(main_server())

if __name__ == "__main__":
    main()