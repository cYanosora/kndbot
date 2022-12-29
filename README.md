<div align="center">
<img width="256px" src="logo.png" alt="奏様">
<br>
<font size=2>总之点进来的人有必要先目睹一下治愈系大天使的尊容.jpg</font>

# KanadeBot
***
[宵崎奏](https://zh.moegirl.org.cn/%E5%AE%B5%E5%B4%8E%E5%A5%8F) 的同人bot一枚，
基于Nonebot2、zhenxun_bot、go-cqhttp开发，使用postgresql作为数据库
<br>活动于QQ群内主要提供
[PJSK](https://mzh.moegirl.org.cn/%E4%B8%96%E7%95%8C%E8%AE%A1%E5%88%92_%E5%BD%A9%E8%89%B2%E8%88%9E%E5%8F%B0_feat._%E5%88%9D%E9%9F%B3%E6%9C%AA%E6%9D%A5)
的服务以及一般娱乐服务
<br>用爱发电⚡ ，希望能凭借bot传教🙏(奏门)
</div>

[//]: # (奏宝她真的是超可爱超可爱🥰🥰，简直是一款所有人的天使😘😘，真的真的，不推奏宝的人可能会失去一些美好品格🥺🥺)
## 重要说明
***
使用的框架为 [**Nonebot**](https://github.com/nonebot/nonebot2) ，一款超好用的 [**OneBot**](https://onebot.dev/) 框架
<br><br>
使用的基础模块引用自 [**绪山真寻bot**](https://github.com/HibiKier/zhenxun_bot) ，一款非常好用的QQ群机器人
<br><br>
其中部分模块出于自己的理解、使用习惯，有大幅修改甚至破坏性变更，所以原有能提供的服务内容还请访问原项目 
### 如何搭建：
此处的版本与正在实际投放使用的版本略有差别，但经测试可以正常搭建，
如果你想搭建此项目<del>(虽然肯定没人搭)</del>，首先需要一台24h不关机的linux主机，
然后只要具有一点点linux基础、数据库基础、nonebot2的使用经验balabala即可轻松获得一只自己的kndbot
<br><br>
没有经验甚至可以参照[**小真寻的文档**](https://hibikier.github.io/zhenxun_bot/)
实现此项目的部署，就不赘述了<del>(这里没有文档，源码就是文档.jpg)</del>
<b>但是纯0基础小白就算了，真心的</b>
### 如何使用：
请直接在有此bot的群内发送kndhelp获取使用说明，**拉群请先加bot好友**

## 功能列表
***
已实现的功能**基本**都是从真寻、
<b>[Nonebot插件商店](https://v2.nonebot.dev/store) </b>
以及别的大佬那里获取并修改后的，与原功能的使用效果可能有一些差异，此处附上项目内使用到的插件repo
<details>
<summary>插件来源列表</summary>

* 烧烤相关 — [Unibot](https://github.com/watagashi-uni/Unibot)
* 点歌 — [MeetWq](https://github.com/noneplugin/nonebot-plugin-simplemusic)
* logo制作 — [MeetWq](https://github.com/noneplugin/nonebot-plugin-logo)
* 头像表情包 — [MeetWq](https://github.com/noneplugin/nonebot-plugin-petpet)
* 表情包制作 — [MeetWq](https://github.com/noneplugin/nonebot-plugin-memes)
* 表情合成 — [MeetWq](https://github.com/noneplugin/nonebot-plugin-emojimix)
* 疯狂星期四 — [KafCoppelia](https://github.com/MinatoAquaCrews/nonebot_plugin_crazy_thursday)
* 今天吃什么 — [KafCoppelia](https://github.com/MinatoAquaCrews/nonebot_plugin_what2eat)
* 语句抽象化 — [CherryCherries](https://github.com/CherryCherries/nonebot-plugin-abstract)
* 60s读世界 — [bingganhe123](https://github.com/bingganhe123/60s-)
* epic免费游戏 — [monsterxcn](https://github.com/monsterxcn/nonebot_plugin_epicfree)
* 天气查询 — [kexue-z](https://github.com/kexue-z/nonebot-plugin-heweather)
* 摸鱼日历 — [A-kirami](https://github.com/A-kirami/nonebot-plugin-moyu)
* 其余未提及的可以在真寻本体及其插件库中寻找，如词库问答、刷屏禁言
</details>

## 其他说明
***
功能列表中提及的烧烤相关的功能需要使用到本地资源库，资源库过于庞大故项目本体<b>不包含</b>此部分资源，
但实现了所需的资源在初次使用到时会先调用相关api获取资源并保存到本地的功能(感谢api的提供者们)
<br><br>
我自己写的功能如<b>获取烧烤同人图、随机消息回复</b>需要与本地资源配合使用，
这部分资源同样由于过于庞大，项目内并<b>不包含</b>，因此搭建后没法直接使用，
但功能本身没有问题，不需要请直接删除
<br><br>
喜欢这只bot提供的服务的各位请一定一定要继续喜欢奏宝，多产点奏宝的粮、多整点奏宝的好活，孩子爱看♥
<br><br>
另外可以赏眼此项目中提及的其他诸多repo，有账号的可以给这些佬点个star支持一下♥

## License
***
AGPL-3.0

移植的功能也好，自己写的也好，都遵循此开源协议