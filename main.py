from datetime import date
from typing import final

import aiohttp
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger
from astrbot.api.message_components import *
import aiofiles
import uuid
import img2pdf

@register("TG2QQ", "Joker42S", "转发TG消息到QQ", "1.0.0")
class TG2QQPlugin(Star):
    def __init__(self, context: Context, config : dict):
        super().__init__(context)
        self.config = config

    async def initialize(self):
        """插件初始化方法"""
        self.plugin_name = "TG2QQ"
        self.sent_failed_imgs = []
        self.base_dir = StarTools.get_data_dir(self.plugin_name)
        # 创建临时目录用于存储下载的图片
        self.temp_dir = self.base_dir / "temp"
        if not self.temp_dir.exists():
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        # 创建持久化目录
        self.persistent_dir = self.base_dir / "persistent"
        if not self.persistent_dir.exists():
            self.persistent_dir.mkdir(parents=True, exist_ok=True)
        self.debug_mode = self.config.get("debug_mode")
        if self.debug_mode:
            self.source_tg = self.config.get("debug_source_tg")
            self.target_qq = self.config.get("debug_target_qq")
            logger.info('调试模式开启，将使用调试配置')
        else:
            self.source_tg = self.config.get("source_tg")
            self.target_qq = self.config.get("target_qq")
            
            # 检查配置是否完整
            if not self.source_tg or not self.target_qq:
                logger.warning("TG2QQ插件配置不完整，请检查source_tg和target_qq配置")
        self.resend_threshold = self.config.get("resend_threshold", 0)

    async def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if self.temp_dir and self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
                logger.info("清理临时文件完成")
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")


    @filter.event_message_type(filter.EventMessageType.ALL, priority=100)
    async def watch_tg_message(self, event: AstrMessageEvent):
        """监听Telegram平台的消息并转发到QQ群"""
        # 检查是否为Telegram平台的消息
        if event.platform_meta.name != "telegram":
            return 
        try:
            if not self.source_tg or not self.target_qq:
                return
            if event.is_private_chat():
                return
            # 检查消息是否来自指定的Telegram源
            if str(event.get_sender_id()) != str(self.source_tg):
                return
            
            # 构建转发消息
            forward_message = MessageChain()
            tg_msg = event.get_messages()
            if self.debug_mode:
                logger.info(f"TG message: {tg_msg}")
                for component in tg_msg:
                    logger.info(f"Debug TG MSG: Component type: {type(component)}, component: {component}")
            for component in tg_msg:
                if isinstance(component, Image) or isinstance(component, File):
                    url = ""
                    if isinstance(component, Image):
                        logger.info(f"Image info, file:{component.file}, url:{component.url}")
                        url = component.url
                    else:
                        logger.info(f"File info, path:{component.file_}, url:{component.url}")
                        url = component.file_
                    # Extract file extension from URL
                    url_extension = url.split('.')[-1] if '.' in url else 'png'
                    if not url_extension in ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tif'):
                        continue
                    file_name = str(uuid.uuid5(uuid.NAMESPACE_URL, url)) + '.' + 'jpg'
                    file_path = self.temp_dir / file_name
                    # logger.info(f'本地图片路径：{file_path}')
                    if not file_path.exists():
                        await self._download_image(url, str(file_path))
                    forward_message.file_image(str(file_path))
                elif isinstance(component, Plain):
                    forward_message.chain.append(component)
                else:
                    logger.info(f"Unkown component type: {type(component)}, component: {component}")
                    if self.debug_mode:
                        forward_message.message(component.toString)
            # 发送转发消息到目标QQ群
            await self.context.send_message(f"aiocqhttp:GroupMessage:{self.target_qq}",forward_message)
            logger.info(f"成功转发消息从TG频道 {self.source_tg} 到QQ群 {self.target_qq}")
            
        except Exception as e:
            logger.error(f"TG2QQ消息转发失败: {e}")
            if forward_message:
                self.sent_failed_imgs.extend(
                    comp.path for comp in forward_message.chain
                    if isinstance(comp, Image)
                )
            if self.resend_threshold == 0 or len(self.sent_failed_imgs) < self.resend_threshold:
                return
            logger.info(f"发送失败图片累计{len(self.sent_failed_imgs)}张，达到重发阈值，开始合并为pdf重发")
            img_paths = self.sent_failed_imgs.copy()
            self.sent_failed_imgs.clear()
            await self._send_pdf(img_paths)
        finally:
            event.stop_event()

    @filter.command("tg_reload")
    async def reload_config(self, event: AstrMessageEvent):
        """重载tg适配器"""
        try:
            platform = self.context.get_platform('telegram')
            if platform == None:
                logger.error("未找到启用状态的TG适配器")
                return
            logger.info("尝试重载TG适配器")
            await platform.terminate()
            await platform.run()
            logger.info("TG适配器已重载")
        except Exception as e:
            logger.error(f"重载TG适配器失败: {e}")

    async def _send_pdf(self, img_paths):
        pdf_path = self.temp_dir / f"{uuid.uuid4()}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(img_paths))
        msg = MessageChain()
        msg.chain = [File(file=str(pdf_path), name=f"TG转发失败图片合集-{date.today().isoformat()}")]
        await self.context.send_message(f"aiocqhttp:GroupMessage:{self.target_qq}",msg)

    async def _download_image(self, url: str, file_path: str, modify_hash = True) -> Path:
        """下载单张图片"""
        try:
            # 设置请求头
            headers = {            
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            }
            
            # 下载图片
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30, proxy=self.proxy) as response:
                    if response.status == 200:
                        img_data = await response.read()
                        if modify_hash:
                            img_data = await _image_obfus(img_data)
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(img_data)
                        
                        logger.info(f"下载图片 {id}: {file_path}")
                        return file_path
                    else:
                        logger.error(f"下载图片失败，状态码: {response.status}")
                        return None
            
        except Exception as e:
            logger.error(f"下载封面图片失败: {e}")
            return None

async def _image_obfus(img_data):
    """破坏图片哈希"""
    from PIL import Image as ImageP
    from io import BytesIO
    import random

    try:
        with BytesIO(img_data) as input_buffer:
            with ImageP.open(input_buffer) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")

                width, height = img.size
                pixels = img.load()

                points = []
                for _ in range(3):
                    while True:
                        x = random.randint(0, width - 1)
                        y = random.randint(0, height - 1)
                        if (x, y) not in points:
                            points.append((x, y))
                            break

                for x, y in points:
                    r, g, b = pixels[x, y]

                    r_change = random.choice([-1, 1])
                    g_change = random.choice([-1, 1])
                    b_change = random.choice([-1, 1])

                    new_r = max(0, min(255, r + r_change))
                    new_g = max(0, min(255, g + g_change))
                    new_b = max(0, min(255, b + b_change))

                    pixels[x, y] = (new_r, new_g, new_b)

                with BytesIO() as output:
                    img.save(output, format="JPEG", quality=95, subsampling=0)
                    return output.getvalue()

    except Exception as e:
        logger.warning(f"破坏图片哈希时发生错误: {str(e)}")
        return img_data
    