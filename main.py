import json
import httpx
from datetime import datetime
from pathlib import Path

from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent

# ========================== 基础配置 ==========================

# 中文语言名到 Google 翻译语言代码的映射
LANGUAGE_MAP = {
    "阿姆哈拉语": "am",
    "阿拉伯语": "ar",
    "巴斯克语": "eu",
    "孟加拉语": "bn",
    "英语（英国）": "en-GB",
    "葡萄牙语（巴西）": "pt-BR",
    "保加利亚语": "bg",
    "加泰罗尼亚语": "ca",
    "切罗基语": "chr",
    "克罗地亚语": "hr",
    "捷克语": "cs",
    "丹麦语": "da",
    "荷兰语": "nl",
    "英语（美国）": "en", "英语": "en",
    "爱沙尼亚语": "et",
    "菲律宾语": "fil",
    "芬兰语": "fi",
    "法语": "fr",
    "德语": "de",
    "希腊语": "el",
    "古吉拉特语": "gu",
    "希伯来语": "iw",
    "印地语": "hi",
    "匈牙利语": "hu",
    "冰岛语": "is",
    "印度尼西亚语": "id",
    "意大利语": "it",
    "日语": "ja",
    "卡纳达语": "kn",
    "韩语": "ko",
    "拉脱维亚语": "lv",
    "立陶宛语": "lt",
    "马来语": "ms",
    "马拉雅拉姆语": "ml",
    "马拉地语": "mr",
    "挪威语": "no",
    "波兰语": "pl",
    "葡萄牙语（葡萄牙）": "pt-PT", "葡萄牙语": "pt-PT",
    "罗马尼亚语": "ro",
    "俄语": "ru",
    "塞尔维亚语": "sr",
    "中文": "zh-CN", "简中": "zh-CN",
    "斯洛伐克语": "sk",
    "斯洛文尼亚语": "sl",
    "西班牙语": "es",
    "斯瓦希里语": "sw",
    "瑞典语": "sv",
    "泰米尔语": "ta",
    "泰卢固语": "te",
    "泰语": "th",
    "繁体中文": "zh-TW", "繁中": "zh-TW",
    "土耳其语": "tr",
    "乌尔都语": "ur",
    "乌克兰语": "uk",
    "越南语": "vi",
    "威尔士语": "cy"
}

# 语言代码反查中文名
REVERSE_LANG_MAP = {v: k for k, v in LANGUAGE_MAP.items()}

# 历史记录路径
HISTORY_PATH = Path("data/plugin_data/translate/history.json")
HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

# ========================== 工具函数 ==========================

def lang_display(code: str) -> str:
    """将语言代码转换为中文名显示"""
    return REVERSE_LANG_MAP.get(code, code)

def is_valid_lang_input(text: str) -> bool:
    """判断输入是否为支持的语言名或语言代码"""
    return text in LANGUAGE_MAP or text in REVERSE_LANG_MAP or text in LANGUAGE_MAP.values()

# ========================== 插件核心类 ==========================

@register("translate", "xu-wish", "使用 Google 翻译文本", "0.1.0")
class GoogleTranslatePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("tl", alias={'翻译', 'fy'})
    async def translate_cmd(self, event: AstrMessageEvent):
        message_text = getattr(event, "message_str", "").strip()
        if not message_text:
            yield event.plain_result("无法获取消息内容。")
            return

        args = message_text.split(maxsplit=2)

        # ======= 使用说明 =======
        if len(args) == 2 and args[1] in {"help", "帮助"}:
            yield event.plain_result(
                "📘 使用说明：\n"
                "/tl <语言> <文本>\n"
                "示例:/tl 日语 今天天气很好\n"
                "输入:/tl 历史 [条数] 查看翻译历史\n"
                "输入:/tl 代码 查看语言代码\n"
                "输入:/tl 你好 自动判断语言并翻译(仅限中英互译)"
            )
            return

        # ======= 输出语言代码表 =======
        if len(args) == 2 and args[1] in {"代码", "code"}:
            text = "\n".join([f"{name.ljust(10)}: {code}" for name, code in LANGUAGE_MAP.items()])
            yield event.plain_result(text)
            return

        # ======= 历史记录 =======
        if len(args) >= 2 and args[1] == "历史":
            history = await self.load_history()
            total = len(history)
            try:
                count = int(args[2]) if len(args) >= 3 else 5
                count = max(1, min(count, 20))
            except ValueError:
                count = 5

            display_count = min(count, total)
            if total == 0:
                yield event.plain_result("暂无翻译记录。")
                return

            text = "\n\n".join([
                f"# {i+1}\n原文: {item['source']}\n翻译: {item['target']}\n语言: {lang_display(item['lang'])}\n时间: {item['time']}"
                for i, item in enumerate(history[-display_count:])
            ])
            yield event.plain_result(text)
            return

        # ======= 自动识别语言 =======
        if len(args) == 2:
            text = args[1]
            try:
                # 根据是否包含中文判断目标语言
                target_lang = "en" if self.is_chinese(text) else "zh-CN"
                translated, detected_lang = await self.translate(text, target_lang)
                yield event.plain_result(translated)
                await self.save_history(text, translated, target_lang)
            except httpx.RequestError:
                yield event.plain_result("无法连接到翻译服务，请检查网络或稍后再试。")
            except Exception as e:
                yield event.plain_result(f"翻译失败：{e}")
            return

        # ======= 指定目标语言翻译 =======
        if len(args) >= 3:
            input_lang = args[1]
            text = args[2]

            # 如果目标语言合法，执行翻译
            if is_valid_lang_input(input_lang):
                target_code = LANGUAGE_MAP.get(input_lang.strip(), input_lang)
                try:
                    translated, detected_lang = await self.translate(text, target_code)
                    yield event.plain_result(translated)
                    await self.save_history(text, translated, target_code)
                except httpx.RequestError:
                    yield event.plain_result("无法连接到翻译服务，请检查网络或稍后再试。")
                except Exception as e:
                    yield event.plain_result(f"翻译失败：{e}")
                return
            else:
                # 否则，将整个字符串合并后作为文本，启用自动识别
                full_text = message_text[len("/tl"):].strip()
                try:
                    target_lang = "en" if self.is_chinese(full_text) else "zh-CN"
                    translated, detected_lang = await self.translate(full_text, target_lang)
                    yield event.plain_result(translated)
                    await self.save_history(full_text, translated, target_lang)
                except httpx.RequestError:
                    yield event.plain_result("无法连接到翻译服务，请检查网络或稍后再试。")
                except Exception as e:
                    yield event.plain_result(f"翻译失败：{e}")
                return

            # 映射语言名或代码
            target_code = LANGUAGE_MAP.get(input_lang.strip().lower(), input_lang)

            try:
                translated, detected_lang = await self.translate(text, target_code)
                yield event.plain_result(translated)
                await self.save_history(text, translated, target_code)
            except httpx.RequestError:
                yield event.plain_result("无法连接到翻译服务，请检查网络或稍后再试。")
            except Exception as e:
                yield event.plain_result(f"翻译失败：{e}")
            return

        yield event.plain_result("用法：/tl <目标语言> <文本>\n例如：/tl 日语 你好")

    def is_chinese(self, text: str) -> bool:
        """判断文本是否包含中文字符"""
        return any('\u4e00' <= ch <= '\u9fff' for ch in text)

    async def translate(self, text: str, target: str) -> (str, str):
        """使用 Google 翻译"""
        async with httpx.AsyncClient(timeout=10) as client:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target,
                "dt": "t",
                "q": text
            }
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            translated = "".join([seg[0] for seg in data[0]])
            detected_lang = data[2]
            return translated, detected_lang

    async def save_history(self, source: str, target: str, lang: str):
        """保存翻译历史，保留最近 20 条"""
        history = await self.load_history()
        history.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "target": target,
            "lang": lang
        })
        HISTORY_PATH.write_text(json.dumps(history[-20:], ensure_ascii=False, indent=2), encoding="utf-8")

    async def load_history(self):
        """加载翻译历史"""
        if not HISTORY_PATH.exists():
            return []
        try:
            return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
