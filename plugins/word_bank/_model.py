import time
from io import BytesIO
import imagehash
from PIL import Image
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    GroupMessageEvent,
    MessageSegment,
)
from services.db_context import db
from typing import Optional, List, Union, Tuple, Any
from datetime import datetime
from configs.path_config import DATA_PATH
import random
from ._config import int2type
from utils.imageutils import get_img_hash
from utils.http_utils import AsyncHttpx
import re
from utils.message_builder import image, face, at


path = DATA_PATH / "word_bank"


class WordBank(db.Model):
    __tablename__ = "word_bank2"

    id = db.Column(db.Integer(), primary_key=True)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.Integer())
    word_scope = db.Column(
        db.Integer(), nullable=False, default=0
    )  # 生效范围 0: 全局 1: 群聊 2: 私聊
    word_type = db.Column(
        db.Integer(), nullable=False, default=0
    )  # 词条类型 0: 完全匹配 1: 模糊 2: 正则
    status = db.Column(db.Boolean(), nullable=False, default=True)  # 词条状态
    problem = db.Column(db.String(), nullable=False)  # 问句
    answer = db.Column(db.String(), nullable=False)  # 答句
    problem_placeholder = db.Column(db.String())  # 问句的占位符
    answer_placeholder = db.Column(db.String())  # 答句的占位符
    create_time = db.Column(db.DateTime(), nullable=False)
    update_time = db.Column(db.DateTime(), nullable=False)

    @classmethod
    async def exist_any_problem(cls, group_id: int) -> bool:
        """
        说明:
            检测群内是否有设置过词条
        参数:
            :param group_id: 群号
        """
        query = cls.query.where(cls.group_id == group_id)
        return bool(await query.gino.first())

    @classmethod
    async def exists(
        cls,
        user_id: Optional[int],
        group_id: Optional[int],
        problem: str,
        answer: Optional[str],
        word_scope: Optional[int] = None,
        word_type: Optional[int] = None,
    ) -> bool:
        """
        说明:
            检测问题是否存在
            用于添加词条时检测词条是否重复
        参数:
            :param user_id: 用户id
            :param group_id: 群号
            :param problem: 问题
            :param answer: 回答
            :param word_scope: 词条范围
            :param word_type: 词条类型
        """
        query = cls.query.where(cls.problem == problem)
        if user_id:
            query = query.where(cls.user_qq == user_id)
        if group_id:
            query = query.where(cls.group_id == group_id)
        if answer:
            query = query.where(cls.answer == answer)
        if word_type:
            query = query.where(cls.word_type == word_type)
        if word_scope:
            query = query.where(cls.word_scope == word_scope)
        return bool(await query.gino.first())

    @classmethod
    async def add_problem_answer(
        cls,
        user_id: int,
        group_id: Optional[int],
        word_scope: int,
        word_type: int,
        problem: Union[str, Message],
        answer: Union[str, Message],
    ):
        """
        说明:
            添加或新增一个问答
        参数:
            :param user_id: 用户id
            :param group_id: 群号
            :param word_scope: 词条范围,
            :param word_type: 词条类型,
            :param problem: 问题
            :param answer: 回答
        """
        # 对问题做处理
        problem, _problem_list = await cls._problem2format(problem, user_id, group_id)
        # 对回答做处理
        answer, _answer_list = await cls._answer2format(answer, user_id, group_id)
        # print(
        #     f"""
        #     qq号：{user_id}
        #     群号：{group_id}
        #     词条范围：{word_scope}
        #     词条匹配类型：{word_type}
        #     问题：{problem}
        #     回答：{answer}
        #     问题的占位符：{",".join(_problem_list)}
        #     回答的占位符：{",".join(_answer_list)}
        #     """
        # )
        if not await cls.exists(user_id, group_id, problem, answer, word_scope, word_type):
            await cls.create(
                user_qq=user_id,
                group_id=group_id,
                word_scope=word_scope,
                word_type=word_type,
                status=True,
                problem=problem.strip(),
                answer=answer.strip(),
                problem_placeholder=",".join(_problem_list),
                answer_placeholder=",".join(_answer_list),
                create_time=datetime.now().replace(microsecond=0),
                update_time=datetime.now().replace(microsecond=0),
            )

    @classmethod
    async def _problem2format(
            cls, problem: Union[str, Message], user_id: int, group_id: int
    ) -> Tuple[str, List[Any]]:
        """
        说明:
            将CQ码转化为特定格式(face、at、image)
            用于添加词条时格式化问句
        参数:
            :param problem: 问题内容
            :param user_id: 用户id
            :param group_id: 群号
        """
        _list = []
        text = ""
        problem = problem if isinstance(problem, Message) else Message(problem)
        for seg in problem:
            if isinstance(seg, str):
                text += seg
            elif seg.type == "text":
                text += seg.data["text"]
            elif seg.type == "face":
                text += f"[face:{seg.data['id']}]"
                _list.append(seg.data['id'])
            elif seg.type == "at":
                text += f"[at:{seg.data['qq']}]"
                _list.append(seg.data['qq'])
            else:
                t = int(time.time())
                _file = (path / "problem" / f"{group_id}" / f"{user_id}_{t}.jpg")
                _file.parent.mkdir(exist_ok=True, parents=True)
                await AsyncHttpx.download_file(seg.data["url"], _file)
                text += f"[image:{str(get_img_hash(_file))}]"
                _list.append(f"problem/{group_id}/{user_id}_{t}.jpg")
        return text, _list

    @classmethod
    async def message2problem(cls, message: Message) -> Union[str, Message]:
        """
        说明:
            将原始Message转化为格式化问题
            用于格式化用户发言便于rule检测中check的进行
        参数:
            :param message: 待转化的message
        """
        # print('发言处理前：', message)
        text = ""
        for seg in message:
            # print(seg)
            if isinstance(seg, str):
                text += seg
            elif seg.type == "text":
                text += seg.data["text"]
            elif seg.type == "face":
                text += f"[face:{seg.data['id']}]"
            elif seg.type == "at":
                text += f"[at:{seg.data['qq']}]"
            else:
                url = seg.data.get("url", None)
                if url:
                    r = await AsyncHttpx.get(url)
                    text += f"[image:{str(imagehash.average_hash(Image.open(BytesIO(r.content))))}]"
        # print('发言处理后：', text)
        return text

    @classmethod
    async def _answer2format(
        cls, answer: Union[str, Message], user_id: int, group_id: int
    ) -> Tuple[str, List[Any]]:
        """
        说明:
            将CQ码转化为占位符(face、at、image)
            用于添加词条时格式化答句
        参数:
            :param answer: 回答内容
            :param user_id: 用户id
            :param group_id: 群号
        """
        answer = answer if isinstance(answer, Message) else Message(answer)
        _list = []
        text = ""
        index = 0
        for seg in answer:
            if isinstance(seg, str):
                text += seg
            elif seg.type == "text":
                text += seg.data["text"]
            elif seg.type == "face":
                text += f"[face:placeholder_{index}]"
                _list.append(seg.data['id'])
            elif seg.type == "at":
                text += f"[at:placeholder_{index}]"
                _list.append(seg.data["qq"])
            else:
                text += f"[image:placeholder_{index}]"
                index += 1
                t = int(time.time())
                _file = path / "answer" / f"{group_id}" / f"{user_id}_{t}.jpg"
                _file.parent.mkdir(exist_ok=True, parents=True)
                await AsyncHttpx.download_file(seg.data["url"], _file)
                _list.append(f"answer/{group_id}/{user_id}_{t}.jpg")
        return text, _list

    @classmethod
    async def _format2answer(
        cls,
        problem: str,
        answer: Union[str, Message],
        user_id: int,
        group_id: int,
        query: Optional["WordBank"] = None,
    ) -> Union[str, Message]:
        """
        说明:
            将占位符转换为CQ码，用于发送答句
        参数:
            :param problem: 问题内容
            :param answer: 回答内容
            :param user_id: 用户id
            :param group_id: 群号
            :param query: 指定查询，用于查看词条指令显示单条问句的所有答句
        """
        if query:
            answer = query.answer
        else:
            query = await cls.query.where(
                (cls.problem == problem)
                & (cls.user_qq == user_id)
                & (cls.group_id == group_id)
                & (cls.answer == answer)
            ).gino.first()
        if query and query.answer_placeholder:
            type_list = re.findall(rf"\[(.*):placeholder_.*]", answer)
            temp_answer = re.sub(rf"\[(.*):placeholder_.*]", "{}", answer)
            seg_list = []
            for t, p in zip(type_list, query.answer_placeholder.split(",")):
                if t == "image":
                    seg_list.append(image(path / p))
                elif t == "face":
                    seg_list.append(face(p))
                elif t == "at":
                    if not query:
                        seg_list.append(at(p))
                    else:
                        seg_list.append(f'[at:{p}]')
            return Message(temp_answer.format(*seg_list))
        return answer

    @classmethod
    async def check(
        cls,
        event: MessageEvent,
        problem: Union[str, Message],
        word_scope: Optional[int] = None,
        word_type: Optional[int] = None,
    ) -> Optional[Union[str, "WordBank", None]]:
        """
        说明:
            检测数据库中是否包含该问句并获取所有答句
            用于匹配用户发言的rule检测
        参数:
            :param event: event
            :param problem: 问句
            :param word_scope: 词条范围 0/1/2:全局/群聊/私聊
            :param word_type: 词条类型 0/1/2:精准/模糊/正则
        """
        query = cls.query
        sql_text = "SELECT * FROM public.word_bank2 where 1 = 1"
        # 救命！！没找到gino的正则表达式方法，暂时使用sql语句
        if word_scope:
            query = query.where(cls.word_scope == word_scope)
            sql_text += f" and word_scope = {word_scope}"
        else:
            # 不指定word_scope时默认获取群聊+全局词条
            if isinstance(event, GroupMessageEvent):
                query = query.where(
                    (cls.group_id == event.group_id) | (cls.word_scope == 0)
                )
                sql_text += f" and (group_id = {event.group_id} or word_scope = 0)"
            else:
                # 不指定word_type时默认获取私聊+全局词条
                query = query.where((cls.word_scope == 2) | (cls.word_scope == 0))
                sql_text += f" and (word_scope = 2 or word_scope = 0)"
        # 获取指定类型的词条
        if word_type:
            query = query.where(cls.word_type == word_type)
            sql_text += f" and word_type = {word_type}"
        # print('提前匹配')
        result = await db.first(db.text(sql_text + f";"))
        # print(result)
        # 完全匹配，word_type:精准 or 图片
        # print('完全匹配中')
        if await query.where(
            (cls.word_type == 0) & (cls.problem == problem)
        ).gino.all():
            # print('匹配成功')
            return query.where(
                (cls.word_type == 0) & (cls.problem == problem)
            )
        # 模糊匹配
        # print('模糊匹配中')
        if await db.first(
            db.text(
                sql_text
                + f" and word_type = 1 and :problem like '%' || problem || '%';"
            ),
            problem=problem,
        ):
            # print('匹配成功')
            return (
                sql_text
                + f" and word_type = 1 and :problem like '%' || problem || '%';"
            )
        # 正则匹配
        # print('正则匹配中')
        if await db.first(
            db.text(
                sql_text
                + f" and word_type = 2 and word_scope != 999 and :problem ~ problem;"
            ),
            problem=problem,
        ):
            # print('匹配成功')
            return (
                sql_text
                + f" and word_type = 2 and word_scope != 999 and :problem ~ problem;"
            )
        # print('匹配失败')

    @classmethod
    async def get_answer(
        cls,
        event: MessageEvent,
        problem: str,
        word_scope: Optional[int] = None,
        word_type: Optional[int] = None,
    ) -> Optional[Union[str, Message]]:
        """
        说明:
            根据问题内容获取随机回答，回答的内容由check方法得到
            用于rule检测成功后返回给用户一条答句
        参数:
            :param event: event
            :param problem: 问题内容
            :param word_scope: 词条范围
            :param word_type: 词条类型
        """
        query = await cls.check(event, problem, word_scope, word_type)
        if query is not None:
            # query为sql语句
            if isinstance(query, str):
                answer_list = await db.all(db.text(query), problem=problem)
                answer = random.choice(answer_list)
                return (
                    await cls._format2answer(answer[6], answer[7], answer[1], answer[2])
                    if answer.answer_placeholder
                    else answer.answer
                )
            # query为gino语句
            else:
                answer_list = await query.gino.all()
                answer = random.choice(answer_list)
                return (
                    await cls._format2answer(
                        problem, answer.answer, answer.user_qq, answer.group_id
                    )
                    if answer.answer_placeholder
                    else answer.answer
                )

    @classmethod
    async def get_problem_all_answer(
        cls,
        problem: str,
        index: Optional[int] = None,
        group_id: Optional[int] = None,
        word_scope: Optional[int] = 0,
    ) -> List[Union[str, Message]]:
        """
        说明:
            获取指定问题所有回答
        参数:
            :param problem: 问题
            :param index: 下标
            :param group_id: 群号
            :param word_scope: 词条范围
        """
        if index is not None:
            if group_id:
                problem = (await cls.query.where(cls.group_id == group_id).gino.all())[index]
            else:
                problem = (
                    await cls.query.where(
                        cls.word_scope == (word_scope or 0)
                    ).gino.all()
                )[index]
            problem = problem.problem
        answer = cls.query.where(cls.problem == problem)
        if group_id:
            answer = answer.where(cls.group_id == group_id)
        return [
            await cls._format2answer("", "", 0, 0, x) for x in (await answer.gino.all())
        ]

    @classmethod
    async def delete_group_problem(
        cls,
        problem: str,
        group_id: int,
        index: Optional[int] = None,
        word_scope: int = 0,
    ):
        """
        说明:
            删除指定问题全部或指定答句
        参数:
            :param problem: 问句
            :param group_id: 群号，无群号时默认查询全局词条
            :param index: 答句下标
            :param word_scope: 词条范围
        """
        # 有下标时删除指定答句
        if index is not None:
            if group_id:
                query = await cls.query.where(
                    (cls.group_id == group_id) & (cls.problem == problem)
                ).gino.all()
            else:
                query = await cls.query.where(
                    (cls.word_scope == word_scope) & (cls.problem == problem)
                ).gino.all()
            await query[index].delete()
        # 无下标时删除全部答句
        else:
            if group_id:
                await WordBank.delete.where(
                    (cls.group_id == group_id) & (cls.problem == problem)
                ).gino.status()
            else:
                await WordBank.delete.where(
                    (cls.word_scope == word_scope) & (cls.problem == problem)
                ).gino.status()

    @classmethod
    async def get_group_all_problem(
        cls, group_id: int
    ) -> List[Tuple[Any, Union[MessageSegment, str]]]:
        """
        说明:
            获取群聊结构化词条列表
        参数:
            :param group_id: 群号
        """
        return cls._handle_problem(
            await cls.query.where(cls.group_id == group_id).gino.all()
        )

    @classmethod
    async def get_problem_by_scope(cls, word_scope: int):
        """
        说明:
            通过词条范围获取结构化词条列表
        参数:
            :param word_scope: 词条范围
        """
        return cls._handle_problem(
            await cls.query.where(cls.word_scope == word_scope).gino.all()
        )

    @classmethod
    async def get_problem_by_type(cls, word_type: int):
        """
        说明:
            通过词条类型获取结构化词条列表
        参数:
            :param word_type: 词条类型
        """
        return cls._handle_problem(
            await cls.query.where(cls.word_type == word_type).gino.all()
        )

    @classmethod
    def _handle_problem(
            cls,
            msg_list: List["WordBank"]
    ) -> List[Tuple[Any, Union[Message, MessageSegment, str]]]:
        """
        说明:
            格式化处理问句，返回元组(格式化前问句，格式化后问句)
        参数:
            :param msg_list: 从数据库取出来的结构化词条列表
        """
        # print('_handle_problem开始')
        _tmp = []
        problem_list = []
        for q in msg_list:
            if q.problem not in _tmp:
                # 含CQ码的问句
                if q.problem_placeholder:
                    type_list = re.findall(rf"\[(image|at|face):.*?]", q.problem)
                    temp_problem = re.sub(rf"\[(image|at|face):.*?]", "{}", q.problem)
                    seg_list = []
                    for t, p in zip(type_list, q.problem_placeholder.split(",")):
                        if t == "image":
                            seg_list.append(image(path / p))
                        elif t == "face":
                            seg_list.append(face(p))
                        elif t == "at":
                            seg_list.append(f'[at:{p}]')
                    fin_problem = Message(temp_problem.format(*seg_list))
                    # print('有图片的问题格式化内容:', fin_problem)
                    problem = (q.problem, fin_problem)
                # 纯文本的问句
                else:
                    problem = (q.problem, f"[{int2type[q.word_type]}] " + q.problem)
                problem_list.append(problem)
                _tmp.append(q.problem)
        # print('格式化后：', problem_list)
        return problem_list

    @classmethod
    async def _move(
        cls,
        user_id: int,
        group_id: Optional[int],
        problem: Union[str, Message],
        answer: Union[str, Message],
        placeholder: str
    ):
        """
        说明:
            旧词条图片移动方法
        参数:
            :param user_id: 用户id
            :param group_id: 群号
            :param problem: 问题
            :param answer: 回答
            :param placeholder: 占位符
        """
        word_scope = 0
        word_type = 0
        # 对图片做额外处理
        if not await cls.exists(user_id, group_id, problem, answer, word_scope, word_type):
            await cls.create(
                user_qq=user_id,
                group_id=group_id,
                word_scope=word_scope,
                word_type=word_type,
                status=True,
                problem=problem,
                answer=answer,
                problem_placeholder=None,
                answer_placeholder=placeholder,
                create_time=datetime.now().replace(microsecond=0),
                update_time=datetime.now().replace(microsecond=0),
            )
