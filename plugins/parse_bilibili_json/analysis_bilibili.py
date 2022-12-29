import re
import aiohttp
import time
import urllib.parse
import json

from services import logger
from utils.http_utils import AsyncHttpx
from utils.message_builder import image

analysis_stat = {}  # analysis_stat: video_url(vurl)


async def bili_keyword(group_id, text):
    try:
        # 提取url
        url, page, time = await extract(text)
        # 如果是小程序就去搜索标题
        if not url:
            pattern = re.compile(r'"desc":".*?"')
            desc = re.findall(pattern, text)
            i = 0
            while i < len(desc):
                title_dict = "{" + desc[i] + "}"
                title = json.loads(title_dict)
                i += 1
                if title["desc"] == "哔哩哔哩":
                    continue
                vurl = await search_bili_by_title(title["desc"])
                if vurl:
                    url, page, time = await extract(vurl)
                    break

        # 获取视频详细信息
        msg, vurl = "", ""
        if "view?" in url:
            # print('B站转发解析：------视频')
            msg, vurl = await video_detail(url, page=page, time=time)
        elif "bangumi" in url:
            # print('B站转发解析：------番剧')
            msg, vurl = await bangumi_detail(url, time)
        elif "xlive" in url:
            # print('B站转发解析：------直播')
            msg, vurl = await live_detail(url)
        elif "article" in url:
            # print('B站转发解析：------专栏')
            msg, vurl = await article_detail(url, page)
        elif "dynamic" in url:
            # print('B站转发解析：------动态')
            msg, vurl = await dynamic_detail(url)

        # 避免多个机器人解析重复推送
        last_vurl = ""
        if group_id:
            if group_id in analysis_stat:
                last_vurl = analysis_stat[group_id]
            analysis_stat[group_id] = vurl
        if last_vurl == vurl:
            return
    except Exception as e:
        logger.warning("bili_keyword Error: {}".format(type(e)))
        return
    return msg


async def b23_extract(text):
    b23 = re.compile(r"b23.tv/(\w+)|(bili(22|23|33|2233).cn)/(\w+)", re.I).search(
        text.replace("\\", "")
    )
    url = f"https://{b23[0]}"
    async with aiohttp.request(
        "GET", url, timeout=aiohttp.client.ClientTimeout(20)
    ) as resp:
        return str(resp.url)


async def extract(text: str):
    try:
        url = ""
        page = re.compile(r"([?&]|&amp;)p=\d+").search(text)
        time = re.compile(r"([?&]|&amp;)t=\d+").search(text)
        aid = re.compile(r"av\d+", re.I).search(text)
        bvid = re.compile(r"BV([A-Za-z0-9]{10})+", re.I).search(text)
        epid = re.compile(r"ep\d+", re.I).search(text)
        ssid = re.compile(r"ss\d+", re.I).search(text)
        mdid = re.compile(r"md\d+", re.I).search(text)
        room_id = re.compile(r"live.bilibili.com/(blanc/|h5/)?(\d+)", re.I).search(text)
        cvid = re.compile(
            r"(/read/(cv|mobile|native)(/|\?id=)?|^cv)(\d+)", re.I
        ).search(text)
        dynamic_id_type2 = re.compile(
            r"(t|m).bilibili.com/(\d+)\?(.*?)(&|&amp;)type=2", re.I
        ).search(text)
        dynamic_id = re.compile(r"(t|m).bilibili.com/(\d+)", re.I).search(text)
        if bvid:
            url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid[0]}"
        elif aid:
            url = f"https://api.bilibili.com/x/web-interface/view?aid={aid[0][2:]}"
        elif epid:
            url = (
                f"https://bangumi.bilibili.com/view/web_api/season?ep_id={epid[0][2:]}"
            )
        elif ssid:
            url = f"https://bangumi.bilibili.com/view/web_api/season?season_id={ssid[0][2:]}"
        elif mdid:
            url = f"https://bangumi.bilibili.com/view/web_api/season?media_id={mdid[0][2:]}"
        elif room_id:
            url = f"https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={room_id[2]}"
        elif cvid:
            page = cvid[4]
            url = f"https://api.bilibili.com/x/article/viewinfo?id={page}&mobi_app=pc&from=web"
        elif dynamic_id_type2:
            url = f"https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail?rid={dynamic_id_type2[2]}&type=2"
        elif dynamic_id:
            url = f"https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail?dynamic_id={dynamic_id[2]}"
        return url, page, time
    except Exception:
        return "", None


async def search_bili_by_title(title: str):
    search_url = f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={urllib.parse.quote(title)}"

    async with aiohttp.request(
        "GET", search_url, timeout=aiohttp.client.ClientTimeout(20)
    ) as resp:
        result = (await resp.json())["data"]["result"]

    for i in result:
        if i.get("result_type") != "video":
            continue
        # 只返回第一个结果
        return i["data"][0].get("arcurl")


# 处理超过一万的数字
def handle_num(num: int):
    if num > 10000:
        num = f"{num / 10000:.2f}万"
    return num


async def video_detail(url, **kwargs):
    try:
        resp = json.loads((await AsyncHttpx.get(url)).text)
        res = resp["data"]
        if not res:
            return "解析到视频被删了/稿件不可见或审核中/权限不足", url
        # async with aiohttp.request(
        #     "GET", url, timeout=aiohttp.client.ClientTimeout(20)
        # ) as resp:
        #     res = (await resp.json()).get("data")
        #     if not res:
        #         return "解析到视频被删了/稿件不可见或审核中/权限不足", url
        vurl = f"https://www.bilibili.com/video/av{res['aid']}"
        title = f"\n{res['title']}\n"
        page = kwargs.get("page")
        if page:
            page = page[0].replace("&amp;", "&")
            p = int(page[3:])
            if p <= len(res["pages"]):
                vurl += f"?p={p}"
                # 添加小标题
                # part = res["pages"][p - 1]["part"]
                # if part != res["title"]:
                #     title += f"小标题：{part}\n"
        urltime = kwargs.get("time")
        if urltime:
            urltime = urltime[0].replace("&amp;", "&")[3:]
            if page:
                vurl += f"&t={urltime}"
            else:
                vurl += f"?t={urltime}"
        pic = image(res["pic"])
        date = time.strftime("%Y-%m-%d", time.localtime(res["ctime"]))
        tname = f"类型：{res['tname']}\nUP：{res['owner']['name']}\n"
        stat = f"上传日期：{date}\n"
        stat += f"播放：{handle_num(res['stat']['view'])}，点赞：{handle_num(res['stat']['like'])}，弹幕：{handle_num(res['stat']['danmaku'])}\n"
        stat += f"收藏：{handle_num(res['stat']['favorite'])}，评论：{handle_num(res['stat']['reply'])}，投币：{handle_num(res['stat']['coin'])}\n"
        desc = f"简介：{res['desc']}"
        desc_list = desc.split("\n")
        desc = ""
        for i in desc_list:
            if i:
                desc += i + "\n"
        desc_list = desc.split("\n")
        if len(desc_list) > 4:
            desc = desc_list[0] + "\n" + desc_list[1] + "\n" + desc_list[2] + "……"
        msg = pic + '\n' + str(vurl) + str(title) + str(tname) + str(stat) + str(desc)
        return msg, vurl
    except Exception as e:
        msg = None
        logger.warning("视频解析出错--Error: {}".format(type(e)))
        return msg, None


async def bangumi_detail(url, time):
    try:
        resp = json.loads((await AsyncHttpx.get(url)).text)
        # async with aiohttp.request(
        #     "GET", url, timeout=aiohttp.client.ClientTimeout(20)
        # ) as resp:
        #     res = (await resp.json()).get("result")
        res = resp["result"]
        if not res:
            return None, None
        title = f"番剧：{res['title']}\n"
        desc = f"{res['newest_ep']['desc']}\n"
        pic = res['cover']
        index_title = ""
        style = ""
        for i in res["style"]:
            style += i + ","
        style = f"类型：{style[:-1]}\n"
        evaluate = f"简介：{res['evaluate']}\n"
        if "season_id" in url:
            vurl = f"https://www.bilibili.com/bangumi/play/ss{res['season_id']}"
        elif "media_id" in url:
            vurl = f"https://www.bilibili.com/bangumi/media/md{res['media_id']}"
        else:
            epid = re.compile(r"ep_id=\d+").search(url)[0][len("ep_id=") :]
            for i in res["episodes"]:
                if str(i["ep_id"]) == epid:
                    index_title = f"标题：{i['index_title']}\n"
                    break
            vurl = f"https://www.bilibili.com/bangumi/play/ep{epid}"
        if time:
            time = time[0].replace("&amp;", "&")[3:]
            vurl += f"?t={time}"
        msg = (
            image(pic)
            + str(vurl)
            + "\n"
            + str(title)
            + str(index_title)
            + str(desc)
            + str(style)
        )
        msg += str(evaluate) if len(evaluate) < 50 else str(evaluate)[:50] + '...'
        return msg, vurl
    except Exception as e:
        msg = None
        logger.warning(f"番剧解析出错--Error: {type(e)}\n{url}")
        return msg, None


async def live_detail(url):
    try:
        resp = json.loads((await AsyncHttpx.get(url)).text)
        res = resp
        if not res:
            return None,None
        # async with aiohttp.request(
        #     "GET", url, timeout=aiohttp.client.ClientTimeout(20)
        # ) as resp:
        #     res = await resp.json()
        #     if res["code"] != 0:
        #         return None, None
        res = res["data"]
        pic = res["room_info"]["cover"]
        uname = res["anchor_info"]["base_info"]["uname"]
        room_id = res["room_info"]["room_id"]
        title = res["room_info"]["title"]
        live_status = res["room_info"]["live_status"]
        lock_status = res["room_info"]["lock_status"]
        parent_area_name = res["room_info"]["parent_area_name"]
        area_name = res["room_info"]["area_name"]
        online = res["room_info"]["online"]
        tags = res["room_info"]["tags"]
        watched_show = res["watched_show"]["text_large"]
        vurl = f"https://live.bilibili.com/{room_id}\n"
        if lock_status:
            lock_time = res["room_info"]["lock_time"]
            lock_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(lock_time))
            title = f"[已封禁]直播间封禁至：{lock_time}\n"
        elif live_status == 1:
            title = f"[直播中]标题：{title}\n"
        elif live_status == 2:
            title = f"[轮播中]标题：{title}\n"
        else:
            title = f"[未开播]标题：{title}\n"
        up = f"主播：{uname}  当前分区：{parent_area_name}-{area_name}\n"
        watch = f"观看：{watched_show}  直播时的人气上一次刷新值：{handle_num(online)}\n"
        if tags:
            tags = f"标签：{tags}\n"
        if live_status:
            player = f"独立播放器：https://www.bilibili.com/blackboard/live/live-activity-player.html?enterTheRoom=0&cid={room_id}"
        else:
            player = ""
        msg = image(pic) + '\n' + str(vurl) + str(title) + str(up) + str(watch) + str(tags) + str(player)
        return msg, vurl
    except Exception as e:
        msg = None
        logger.warning("直播间解析出错--Error: {}".format(type(e)))
        return msg, None


async def article_detail(url, cvid):
    try:
        resp = json.loads((await AsyncHttpx.get(url)).text)
        res = resp["data"]
        if not res:
            return None, None
        # async with aiohttp.request(
        #     "GET", url, timeout=aiohttp.client.ClientTimeout(20)
        # ) as resp:
        #     res = (await resp.json()).get("data")
        #
        #     if not res:
        #         return None, None
        vurl = f"https://www.bilibili.com/read/cv{cvid}\n"
        title = f"标题：{res['title']}\n"
        pic = res['banner_url']
        up = f"作者：{res['author_name']} (https://space.bilibili.com/{res['mid']})\n"
        view = f"阅读数：{handle_num(res['stats']['view'])}，"
        favorite = f"收藏：{handle_num(res['stats']['favorite'])}\n"
        coin = f"投币：{handle_num(res['stats']['coin'])}，"
        share = f"分享：{handle_num(res['stats']['share'])}\n"
        like = f"点赞：{handle_num(res['stats']['like'])}，"
        dislike = f"不喜欢：{handle_num(res['stats']['dislike'])}"
        desc = view + favorite + coin + "\n" + share + like + dislike
        msg = image(pic) + ('\n' if pic else "") + str(vurl) + "，" + str(title) + str(up) + str(desc)
        return msg, vurl
    except Exception as e:
        # msg = "专栏解析出错--Error: {}".format(type(e))
        msg = None
        logger.warning("专栏解析出错--Error: {}".format(type(e)))
        return msg, None


async def dynamic_detail(url):
    try:
        resp = json.loads((await AsyncHttpx.get(url)).text)
        res = resp["data"].get("card")
        if not res:
            return None, None
        # async with aiohttp.request(
        #     "GET", url, timeout=aiohttp.client.ClientTimeout(20)
        # ) as resp:
        #     res = (await resp.json())["data"].get("card")
        #
        #     if not res:
        #         return None, None
        card = json.loads(res["card"])
        dynamic_id = res["desc"]["dynamic_id"]
        vurl = f"https://t.bilibili.com/{dynamic_id}\n"
        item = card.get("item")
        if not item:
            return "动态不存在文字内容", vurl
        content = item.get("description")
        if not content:
            content = item.get("content")
        content = content.replace("\r\n", "\n")
        content = content.replace("\r", "\n")
        if len(content) > 250:
            content = content[:250] + "......"
        pics = item.get("pictures_count")
        if pics:
            if pics == 1:
                pic = item["pictures"][0]['img_src']
                content += image(pic)
            else:
                content += f"\nPS：动态中包含{pics}张图片"
        origin = card.get("origin")
        if origin:
            jorigin = json.loads(origin)
            short_link = jorigin.get("short_link")
            if short_link:
                content += f"\n动态包含转发视频{short_link}"
            else:
                content += f"\n动态包含转发其他动态"
        msg = str(vurl) + str(content)
        return msg, vurl
    except Exception as e:
        msg = "动态解析出错--Error: {}".format(type(e))
        return msg, None