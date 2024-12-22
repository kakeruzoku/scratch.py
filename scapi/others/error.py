from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from others.common import Response
    from sites.base import _BaseSiteAPI

"""
階層表記
- HTTPError 通信時でのエラー
  - SessionClosed セッションが閉じてた
  - HTTPFetchError レスポンスが帰って来なかった
  - ResponseError 応答でエラーが起こった
    - BadResponse {"code":"BadRequest","message":""} が帰ってきた
    - BadRequest 4xx
      - Unauthorized 401 or 403
      - HTTPNotFound 404
      - TooManyRequests 429
    - ServerError 5xx
- NoSession セッションなし
  - NoPermission 権限なし
- LoginFailure ログイン失敗
- ObjectFetchError get_objectでエラー
  - ObjectNotFound get_objectでなかったとき
    - SessionNotFound Sessionがなかった時
    - UserNotFound ユーザーない
    - ProjectNotFound プロジェクトない
    - StudioNotFound スタジオない
    - CommentNotFound コメントない
- NoDataError Partial系のデータで、データが存在しないとき
"""

# http
class HTTPError(Exception):
    """
    通信でエラーが起きた時に出る
    """
class SessionClosed(Exception):
    """
    クライアントセッションが閉じてたときにでる
    """
class HTTPFetchError(HTTPError):
    """
    通信で失敗(レスポンスが返ってこなかったなど)したときに出る
    """
class ResponseError(HTTPError):
    """
    応答したが、エラーが起きた時に出る
    """
    def __init__(self, status_code:int, response:"Response"):
        self.status_code:int = status_code
        self.response:"Response" = response
class BadResponse(ResponseError):
    """
    {"code":"BadRequest","message":""}
    """
class BadRequest(ResponseError):
    """
    400番台が出た時に出す。
    """
class Unauthorized(BadRequest):
    """
    認証失敗(401/403)
    """
class HTTPNotFound(BadRequest):
    """
    404
    """
class TooManyRequests(BadRequest):
    """
    429
    """
class ServerError(ResponseError):
    """
    500が出た時
    """

class NoSession(Exception):
    """
    セッションが必要な操作をセッションなしで実行しようとした。
    """
class NoPermission(NoSession):
    """
    権限がない状態で実行しようとした。
    """

class LoginFailure(Exception):
    """
    ログイン失敗
    """

class ObjectFetchError(Exception):
    """
    getしたけどエラー出た
    """
    def __init__(self,Class:"_BaseSiteAPI.__class__",error):
        self.Class = Class
        self.error = error
class ObjectNotFound(ObjectFetchError):
    """
    getしたけどなかったてきなやつ
    """
class SessionNotFound(ObjectNotFound):
    """
    セッションでのログインに失敗
    """
class UserNotFound(ObjectNotFound):
    """
    ユーザーの取得に失敗
    """
class ProjectNotFound(ObjectNotFound):
    """
    プロジェクトの取得に失敗
    """
class StudioNotFound(ObjectNotFound):
    """
    スタジオの取得に失敗
    """
class CommentNotFound(ObjectNotFound):
    """
    コメント取得失敗
    """

class NoDataError(Exception):
    """
    データ不足
    """