# -*- coding: utf-8 -*-
from odoo import http

# class OdooRabbitmq(http.Controller):
#     @http.route('/odoo_rabbitmq/odoo_rabbitmq/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo_rabbitmq/odoo_rabbitmq/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo_rabbitmq.listing', {
#             'root': '/odoo_rabbitmq/odoo_rabbitmq',
#             'objects': http.request.env['odoo_rabbitmq.odoo_rabbitmq'].search([]),
#         })

#     @http.route('/odoo_rabbitmq/odoo_rabbitmq/objects/<model("odoo_rabbitmq.odoo_rabbitmq"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo_rabbitmq.object', {
#             'object': obj
#         })