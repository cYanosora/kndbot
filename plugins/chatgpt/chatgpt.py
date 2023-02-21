import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from nonebot import get_driver
from nonebot.log import logger
from nonebot.utils import escape_tag
from playwright.async_api import Page, Route, async_playwright

driver = get_driver()
try:
    import ujson as json
except ModuleNotFoundError:
    import json


SESSION_TOKEN_KEY = "__Secure-next-auth.session-token"


class Chatbot:
    """ 用于请求openai官网获取回复的主体处理程序，由异步playwright实现 """
    def __init__(
        self,
        *,
        token: str = "",
        account: str = "",
        password: str = "",
        api: str = "https://chat.openai.com",
        proxies: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        self.session_token = token
        self.account = account
        self.password = password
        self.api_url = api
        self.proxies = proxies
        self.timeout = timeout
        self.content = None
        self.parent_id = None
        self.conversation_id = None
        self.browser = None
        self.playwright = async_playwright()
        if self.session_token:
            self.auto_auth = False
        elif self.account and self.password:
            self.auto_auth = True
        else:
            raise ValueError("至少需要配置 session_token 或者 account 和 password")

    async def playwright_start(self):
        """启动浏览器，在插件开始运行时调用"""
        playwright = await self.playwright.start()
        try:
            self.browser = await playwright.firefox.launch(
                headless=True,
                proxy={"server": self.proxies} if self.proxies else None,  # your proxy
            )
        except Exception as e:
            logger.opt(exception=e).error("playwright未安装，请先在shell中运行playwright install")
            return
        ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/{self.browser.version}"
        self.content = await self.browser.new_context(user_agent=ua)
        await self.set_cookie(self.session_token)

    async def set_cookie(self, session_token: str):
        """设置session_token"""
        self.session_token = session_token
        await self.content.add_cookies([{
            "name": SESSION_TOKEN_KEY,
            "value": session_token,
            "domain": "chat.openai.com",
            "path": "/",
        }])

    @driver.on_shutdown
    async def playwright_close(self):
        """关闭浏览器"""
        await self.content.close()
        await self.browser.close()
        await self.playwright.__aexit__()

    def __call__(
        self, conversation_id: Optional[str] = None, parent_id: Optional[str] = None
    ):
        self.conversation_id = conversation_id[-1] if conversation_id else None
        self.parent_id = parent_id[-1] if parent_id else self.id
        return self

    @property
    def id(self) -> str:
        """ 使用uuid记录会话id """
        return str(uuid.uuid4())

    def get_payload(self, prompt: str) -> Dict[str, Any]:
        """ 传给api的数据结构"""
        return {
            "action": "next",
            "messages": [{
                "id": self.id,
                "role": "user",
                "content": {"content_type": "text", "parts": [prompt]},
            }],
            "conversation_id": self.conversation_id,
            "parent_message_id": self.parent_id,
            "model": "text-davinci-002-render",
        }

    @asynccontextmanager
    async def get_page(self):
        """打开网页，这是一个异步上下文管理器，使用async with调用"""
        if self.content is None:
            await self.playwright_start()
        page = await self.content.new_page()
        js = "Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});"
        await page.add_init_script(js)
        await page.goto(self.api_url + "/chat")
        yield page
        await page.close()

    async def get_chat_response(self, prompt: str) -> str:
        """获取问题的回复"""
        async with self.get_page() as page:
            await page.wait_for_load_state("domcontentloaded")
            # 若需要过cf cookie验证
            cf_flag = True
            if not await page.locator("text=Log out").count():
                cf_flag = await self.get_cf_cookies(page)
            if not cf_flag:
                return f"未能通过网站验证码校验，请重新尝试"
            logger.debug("正在发送请求")

            async def change_json(route: Route):
                await route.continue_(
                    post_data=json.dumps(self.get_payload(prompt)),
                )

            await self.content.route(
                self.api_url + "/backend-api/conversation", change_json
            )
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_load_state("networkidle")
            # 网页完全加载后开始操作
            session_expired = page.locator("button", has_text="Log in")
            # session过期，需要重新设置session
            if await session_expired.is_visible():
                logger.warning("检测到session过期")
                return "token失效，请重新设置token"
            # 处理首次打开网页时会出现的弹窗
            next_botton = page.locator(".btn.flex.justify-center.gap-2.btn-neutral.ml-auto")
            await page.wait_for_timeout(1000)
            if await next_botton.is_visible():
                logger.debug("检测到初次打开弹窗")
                await next_botton.click()
                await next_botton.click()
                await page.click(".btn.flex.justify-center.gap-2.btn-primary.ml-auto")
            # 输入问题，等待chatgpt响应
            async with page.expect_response(
                self.api_url + "/backend-api/conversation",
                timeout=self.timeout * 1000,
            ) as response_info:
                textarea = page.locator("textarea")
                botton = page.locator('button[class="absolute p-1 rounded-md text-gray-500 bottom-1.5 right-1 md:bottom-2.5 md:right-2 hover:bg-gray-100 dark:hover:text-gray-400 dark:hover:bg-gray-900 disabled:hover:bg-transparent dark:disabled:hover:bg-transparent"]')
                logger.debug("正在等待回复")
                # 多次尝试确保点中了问题文本框
                for _ in range(3):
                    await textarea.fill(prompt)
                    # await textarea.press("Enter")
                    if await botton.is_enabled():
                        await botton.click()
                        break
                    await page.wait_for_timeout(500)
                response = await response_info.value
                # 处理异常响应码
                if response.status == 429:
                    await page.close()
                    return "网站处理的请求过多，请之后再来尝试吧"
                if response.status == 403:
                    await self.get_cf_cookies(page)
                    await page.close()
                    return await self.get_chat_response(prompt)
                if response.status != 200:
                    try:
                        logger.opt(colors=True).error(
                            f"非预期的响应内容: <r>HTTP{response.status}</r> {escape_tag(response.text)}"
                        )
                    except:
                        logger.error(
                            f"非预期的响应内容: <r>HTTP{response.status}</r> {response.text}"
                        )
                    await page.close()
                    return f"ChatGPT 服务器返回了非预期的内容: HTTP{response.status}\n{response.text}"
                # 正常响应，返回chatgpt的回复
                logger.info('ChatGPT 正确返回了请求')
                lines = None
                error = None
                for _ in range(2):
                    try:
                        lines = await response.text()
                        if lines is not None:
                            break
                    except Exception as e:
                        error = e
                if lines is None:
                    raise error
                lines = lines.splitlines()
                data = lines[-4][6:]  # 最后一次收到的文本数据，去掉开头6个字符(data: )
                response = json.loads(data)
                self.parent_id = response["message"]["id"]
                self.conversation_id = response["conversation_id"]
        return response["message"]["content"]["parts"][0]

    async def refresh_session(self) -> None:
        """ 刷新token """
        logger.debug("正在刷新session")
        # 若初始化时没有设置token只设置了账号密码，使用账号密码登录刷新token
        if self.auto_auth:
            await self.login()
        # 若初始化时设置了token，使用旧token获取新token
        else:
            async with self.get_page() as page:
                if not await page.locator("text=Log out").is_visible():
                    cf_flag = await self.get_cf_cookies(page)
                await page.wait_for_load_state("domcontentloaded")
                # 初始化的token已经过期
                session_expired = page.locator("text=Your session has expired")
                if await session_expired.count():
                    logger.opt(colors=True).error("刷新会话失败, session token 已过期, 请重新设置")
            # 重新设置token
            cookies = await self.content.cookies()
            for i in cookies:
                if i["name"] == SESSION_TOKEN_KEY:
                    self.session_token = i["value"]
                    break
            logger.debug("刷新会话成功")

    async def login(self) -> None:
        """
        使用当前账号信息登录openai获取token
        """
        from OpenAIAuth.OpenAIAuth import OpenAIAuth

        auth = OpenAIAuth(self.account, self.password, bool(self.proxies), self.proxies)  # type: ignore
        try:
            auth.begin()
        except Exception as e:
            if str(e) == "Captcha detected":
                logger.error("登录过程遇到验证码, 请使用 session token")
            raise e
        if not auth.access_token:
            logger.error("ChatGPT 登陆错误!")
        # 重新设置token
        if auth.session_token:
            await self.set_cookie(auth.session_token)
        elif possible_tokens := auth.session.cookies.get(SESSION_TOKEN_KEY):
            if len(possible_tokens) > 1:
                await self.set_cookie(possible_tokens[0])
            else:
                try:
                    await self.set_cookie(possible_tokens)
                except Exception as e:
                    logger.opt(exception=e).error("ChatGPT 登陆错误!")
        else:
            logger.error("ChatGPT 登陆错误!")

    @staticmethod
    async def get_cf_cookies(page: Page) -> bool:
        """ 尝试过openai的cf cookie验证 """
        logger.info("正在获取cf cookies")
        for _ in range(20):
            # 可能有两种验证按钮
            button = page.get_by_role("button", name="Verify you are human")
            if await button.count():
                await button.click()
            try:
                label = page.frame_locator(
                    "iframe[title=\"Widget containing a Cloudflare security challenge\"]"
                ).get_by_label("Verify you are human")
                if await label.count():
                    await label.check()
            except:
                pass
            await page.wait_for_timeout(1000)
            cf = page.locator("text=Log out")
            if await cf.is_visible():
                break
        else:
            logger.error("cf cookies获取失败")
            return False
        logger.info("cf cookies获取成功")
        return True
