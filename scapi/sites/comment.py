import datetime
import random
from typing import AsyncGenerator, Literal, TypedDict, TYPE_CHECKING, overload
import warnings

import others.common as common
import others.error as exception
import sites.base as base

if TYPE_CHECKING:
    from sites.session import Session
    from sites.user import User
    from sites.studio import Studio
    from sites.project import Project

class CommentData(TypedDict):
    place:"Project|Studio"
    id:int
    data:dict|None


class Comment(base._BaseSiteAPI):
    raise_class = exception.CommentNotFound
    id_name = "data"

    def __init__(
        self,
        ClientSession:common.Requests,
        data:CommentData,
        scratch_session:"Session|None"=None,
        **entries
    ) -> None:
        from sites.user import User
        from sites.studio import Studio
        from sites.project import Project
        
        self.place:Project|Studio = data.get("place")
        self.id:int = data.get("id")
        self.type:Literal["Project"]|Literal["Studio"] = None

        if isinstance(self.place,Project):
            self.type = "Project"
            super().__init__("get",
                f"https://api.scratch.mit.edu/users/{self.place.author.username}/projects/{self.place.id}/comments/{self.id}",
                ClientSession,scratch_session
            )
        elif isinstance(self.place,Studio):
            self.type = "Studio"
            super().__init__("get",
                f"https://api.scratch.mit.edu/studios/{self.place.id}/comments/{self.id}",
                ClientSession,scratch_session
            )
        else:
            raise ValueError
            
        self.parent_id:int|None = None
        self.commentee_id:None = None
        self.content:str = None
        self.sent_dt:datetime.datetime = None
        self.author:User = None
        self.reply_count:int = None

        self._parent_cache:"Comment|None" = None
        if data.get("data",None) is not None:
            self._update_from_dict(data.get("data"))

    @property
    def _is_me(self) -> bool:
        if isinstance(self.Session,Session):
            if self.Session.username == self.author.username:
                return True
        return False
    
    def _is_me_raise(self) -> None:
        if not self._is_me:
            raise exception.NoPermission

    def _update_from_dict(self, data:dict) -> None:
        from sites.user import User
        self.parent_id = data.get("parent_id",self.parent_id)
        self.commentee_id = data.get("commentee_id",self.commentee_id)
        self.content = data.get("content",self.content)
        self.sent_dt = common.to_dt(data.get("datetime_create"),self.sent_dt)
        _author:dict = data.get("author",{})
        self.author = User(
            self.ClientSession,_author.get("username")
        )
        self.author._update_from_dict(_author)
        self.reply_count = data.get("reply_count",self.reply_count)

    async def get_parent_comment(self,use_cache:bool=True) -> "Comment|None":
        if (self._parent_cache is not None) and (use_cache):
            return self._parent_cache
        if self.parent_id is None:
            return None
        self._parent_cache = await self.place.get_comment_by_id(self.parent_id)
        return self._parent_cache
        
    
    def get_replies(self, *, limit=40, offset=0) -> AsyncGenerator["Comment",None]:
        return base.get_comment_iterator(
            self.place,f"{self.update_url}/replies/",
            limit=limit,offset=offset,add_params={"cachebust":random.randint(0,9999)}
        )

    async def reply(self, content, *, commentee_id=None) -> "Comment":
        return await self.place.post_comment(
            content,commentee_id=self.author.id if commentee_id is None else commentee_id,
            parent_id=self.id if self.parent_id is None else self.parent_id
        )

    async def delete(self) -> bool:
        self.has_session()
        if self.type == "Project":
            return (await self.ClientSession.delete(f"https://api.scratch.mit.edu/proxy/comments/project/{self.place.id}/comment/{self.id}",data="{}")).status_code == 200
        elif self.type == "Studio":
            return (await self.ClientSession.delete(f"https://api.scratch.mit.edu/proxy/comments/studio/{self.place.id}/comment/{self.id}",data="{}")).status_code == 200

    async def report(self) -> bool:
        self.has_session()
        if self.type == "Project":
            return (await self.ClientSession.post(f"https://api.scratch.mit.edu/proxy/project/{self.place.id}/comment/{self.id}/report",json={"reportId":None})).status_code == 200
        elif self.type == "Studio":
            return (await self.ClientSession.post(f"https://api.scratch.mit.edu/proxy/studio/{self.place.id}/comment/{self.id}/report",json={"reportId":None})).status_code == 200

class UserComment(Comment):
    def __init__(self,user,ClientSession,scratch_session):
        self._csid:bytes = random.randbytes(32)
        self.ClientSession:common.Requests = ClientSession
        self.update_type = ""
        self.update_url = ""
        self.Session:Session|None = scratch_session
        self._raw:dict = None

        self.place:User = user
        self.id:int = None
        self.type:Literal["User"] = "User"

        self.parent_id:int|None = None
        self.commentee_id:int|None = None
        self.content:str = None
        self.sent_dt:datetime.datetime = None
        self.author:User = None
        self.reply_count:int = None

        self._parent_cache:"UserComment|None" = None
        self._reply_cache:"list[UserComment]" = None
        
    async def update(self):
        warnings.warn(f"The update will take some time.")
        r = await self.place.get_comment_by_id(self.id)
        self.parent_id = r.parent_id
        self.commentee_id = r.commentee_id
        self.content = r.content
        self.sent_dt = r.sent_dt
        self.author = r.author
        self.reply_count = r.reply_count
        self._parent_cache = r._parent_cache
        self._reply_cache = r._reply_cache

    def _update_from_dict(self, data:dict) -> None:
        super()._update_from_dict(data)
        self._reply_cache = data.get("_reply_cache",[])
        self.id = data.get("id")
        self._parent_cache = data.get("_parent_cache",None)

    async def get_replies(self, *, limit=40, offset=0) -> AsyncGenerator["UserComment",None]:
        for i in self._reply_cache[offset:offset+limit]:
            yield i

    async def reply(self, content, *, commentee_id=None) -> "UserComment":
        return await self.place.post_comment(
            content,commentee_id=self.author.id if commentee_id is None else commentee_id,
            parent_id=self.id if self.parent_id is None else self.parent_id
        )

    async def delete(self) -> bool:
        return (await self.ClientSession.post(
            f"https://scratch.mit.edu/site-api/comments/user/{self.place.username}/del/",
            json={"id":str(self.id)})).status_code == 200
    
    async def report(self) -> bool:
        return (await self.ClientSession.post(
            f"https://scratch.mit.edu/site-api/comments/user/{self.place.username}/rep/",
            json={"id":str(self.id)})).status_code == 200