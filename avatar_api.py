"""Personal photo preferences and bounded, re-encoded image uploads."""
import base64
import binascii
import io
import warnings
from fastapi import Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from PIL import Image, ImageOps, UnidentifiedImageError
from security import IdentityStore
from account_api import profile

class Upload(BaseModel):
    image: str = Field(max_length=5600000)

class Options(BaseModel):
    gravatar_enabled: bool
    clear: bool = False

def sanitise_image(encoded):
    try:
        data=base64.b64decode(encoded,validate=True)
        if len(data)>4*1024*1024:raise ValueError()
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in ('PNG','JPEG','WEBP') or source.width*source.height>16000000:raise ValueError()
                source.load()
                photo=ImageOps.exif_transpose(source).convert('RGBA')
                photo.thumbnail((512,512))
                clean=Image.new('RGBA',photo.size);clean.paste(photo)
                output=io.BytesIO();clean.save(output,format='PNG',optimize=True)
                return output.getvalue()
    except (ValueError,binascii.Error,OSError,SyntaxError,UnidentifiedImageError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise HTTPException(422,'Choose a PNG, JPEG or WebP image under 4 MB and 16 megapixels.')

def install(app,backend):
    def user(request,write=False):
        store=IdentityStore(backend.monitor);identity=store.authenticate(request)
        if write:store.same_origin(request)
        return identity

    @app.get('/user/avatar/{user_id}',include_in_schema=False)
    def avatar(request:Request,user_id:int):
        identity=user(request)
        if identity['id']!=user_id and 'admin' not in identity['permissions']:raise HTTPException(403,'Permission denied')
        with backend.monitor.connect() as db:row=db.execute('SELECT avatar_upload FROM users WHERE id=?',(user_id,)).fetchone()
        if not row or not row[0]:raise HTTPException(404,'Photo unavailable')
        return Response(row[0],media_type='image/png',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

    @app.post('/user/photo',include_in_schema=False)
    def upload(request:Request,body:Upload):
        identity=user(request,True)
        return save_upload(identity['id'],body)

    def save_upload(user_id,body):
        data=sanitise_image(body.image)
        with backend.monitor.connect() as db:
            result=db.execute("UPDATE users SET avatar_upload=?,photo='',version=version+1 WHERE id=?",(data,user_id))
            if not result.rowcount:raise HTTPException(404,'User not found')
            return profile(db,user_id)

    @app.patch('/user/photo',include_in_schema=False)
    def options(request:Request,body:Options):
        identity=user(request,True)
        return save_options(identity['id'],body)

    def save_options(user_id,body):
        with backend.monitor.connect() as db:
            result=db.execute('UPDATE users SET gravatar_enabled=?,version=version+1 WHERE id=?',(body.gravatar_enabled,user_id))
            if not result.rowcount:raise HTTPException(404,'User not found')
            if body.clear:db.execute("UPDATE users SET avatar_upload=NULL,photo='' WHERE id=?",(user_id,))
            return profile(db,user_id)

    @app.post('/administration/users/{user_id}/photo',include_in_schema=False)
    def admin_upload(request:Request,user_id:int,body:Upload):
        identity=user(request,True)
        IdentityStore(backend.monitor).require(identity,'admin')
        return save_upload(user_id,body)

    @app.patch('/administration/users/{user_id}/photo',include_in_schema=False)
    def admin_options(request:Request,user_id:int,body:Options):
        identity=user(request,True)
        IdentityStore(backend.monitor).require(identity,'admin')
        return save_options(user_id,body)
