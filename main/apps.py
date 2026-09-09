from django.apps import AppConfig


class MainConfig(AppConfig):
    name = "main"

    def ready(self):
        # SimpleUI 会在自身初始化时移除该中间件；前台与后台都仍需要防点击劫持响应头。
        from django.conf import settings

        middleware = "django.middleware.clickjacking.XFrameOptionsMiddleware"
        if middleware not in settings.MIDDLEWARE:
            settings.MIDDLEWARE.append(middleware)
