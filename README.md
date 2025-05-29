# AstrBot Plugin - Google翻译插件

这是一个使用 Google Translate 的 AstrBot 插件，支持使用命令 `/tl` 翻译任意文本。

## ✅ 特性

- 使用异步方式调用 Google Translate 公共接口
- 支持中英文语言名称（如 `/tl 日语 你好`）
- 翻译历史记录自动持久化（`data/plugin_translate/history.json`）
- 支持命令：  
  - `/tl <语言> <内容>`  
  - `/tl 历史 [条数] 查看翻译历史`
  - `/tl help 查看帮助`
  - `/tl code 查看语言代码`
  - `/tl 你好 自动判断语言并翻译(仅限中英互译)`

## 📦 安装依赖

```bash
pip install -r requirements.txt
