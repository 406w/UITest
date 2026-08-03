"""PageRedirect 层：页面跳转关系。

跳转来源（ComeFrom）声明在本层，每个页面一个声明文件（<页面>_page_redirects.py），
导入即注册到对应页面类；本层同时提供跳转关系查询函数。
"""
from .page_redirect import PageRedirect
from . import login_page_redirects, home_page_redirects

__all__ = ["PageRedirect"]
