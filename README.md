# AstrBot TG2QQ 插件

一个自动搬运TG消息到QQ的AstrBot插件

## ✅ 已实现功能
- [x] 转发图片内容
- [x] 转发文本内容

## 🚧 计划功能
- [ ] 配置多个转发源和目标
- [ ] 消息源白名单和黑名单机制
- [ ] 可配置的临时文件清理策略
- [ ] 监听 telegram 消息平台的连接情况并在断线时重连

## 📦 环境要求
- 安装AstrBot
- 创建Telegram机器人
- 可访问Telegram的网络环境

## 🛠️ 安装步骤

1. **克隆插件到AstrBot插件目录**
```bash
cd /path/to/astrbot/plugins
git clone https://github.com/Joker42S/astrbot_plugin_tg2qq.git
```
  
2. **重启AstrBot**
 
3. **配置参数**
   - 添加Telegram消息平台，可参考：[官方接入教程](https://astrbot.app/deploy/platform/telegram.html)
   - 在插件配置中设置Telegram ID，QQ 群号

## 📖 使用方法

使用配置中的 Telegram 账号发送消息到 Telegram Bot 所在的群聊或频道，
消息中的文本与图片内容会被逐条转发到QQ群

## ⚙️ 配置说明
Telegram ID ： 转发该账号发送的消息
目标 QQ 群号 ： 转发到该QQ群（或QQ号）
调试模式 ：打开时，转发源和目标使用调试配置
调试用 Telegram ID，调试用 QQ 群号 ： 调试配置

## 📁 文件目录

下载的图片等多媒体文件保存在 `AstrBot/data\plugin_data\TG2QQ\temp`
目前没有做清理策略，如果不需要保留，请手动清理

## 📄 许可证

本项目遵循开源许可证，具体许可证信息请查看项目根目录下的 LICENSE 文件。

## 🙏 特别感谢

- [AstrBot](https://github.com/Soulter/AstrBot) - AstrBot平台
