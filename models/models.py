#!/usr/bin/python3
# @Time    : 2019-09-09
# @Author  : Kevin Kong (kfx2007@163.com)

from odoo import api, fields, models, _
import pika
import logging
import traceback
from odoo.exceptions import AccessError, ValidationError, Warning
from odoo.tools.safe_eval import safe_eval, test_python_expr
import threading


_logger = logging.getLogger(__name__)


class RabbitmqSever(models.Model):
    _name = "rabbitmq.server"
    _inherit = 'ir.actions.actions'

    name = fields.Char("服务名称")
    host = fields.Char("服务器地址")
    user = fields.Char("用户名")
    password = fields.Char("密码")
    port = fields.Integer("端口", default=5672)
    channel_number = fields.Integer("通道编号")
    type = fields.Selection(
        selection=[('produce', '生产者'), ('consumer', '消费者')], string="角色")
    routing_key = fields.Char("路由关键字")
    exchange = fields.Char("交换机")
    queue_name = fields.Char("队列名称", default="")
    exchange_type = fields.Selection(selection=[("direct", "Direct"), ("fanout", "Fanout"),
                                                ("topic", "Topic"), ("headers", "Headers")], string="交换类型")
    model_id = fields.Many2one("ir.model", "回调模型")
    code = fields.Text("回调方法")
    state = fields.Selection(
        [('stopped', '已停止'), ('running', '运行中')], string="状态")

    @api.constrains('code')
    def _check_python_code(self):
        for action in self.sudo().filtered('code'):
            msg = test_python_expr(expr=action.code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    @api.model
    def _get_eval_context(self, action=None):
        """ Prepare the context used when evaluating python code, like the
        python formulas or code server actions.

        :param action: the current server action
        :type action: browse record
        :returns: dict -- evaluation context given to (safe_)safe_eval """
        def log(message, level="info"):
            with self.pool.cursor() as cr:
                cr.execute("""
                    INSERT INTO ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func)
                    VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (self.env.uid, 'server', self._cr.dbname, __name__, level, message, "action", action.id, action.name))

        eval_context = super(
            RabbitmqSever, self)._get_eval_context(action=action)
        model_name = action.model_id.sudo().model
        model = self.env[model_name]
        record = None
        records = None
        if self._context.get('active_model') == model_name and self._context.get('active_id'):
            record = model.browse(self._context['active_id'])
        if self._context.get('active_model') == model_name and self._context.get('active_ids'):
            records = model.browse(self._context['active_ids'])
        if self._context.get('onchange_self'):
            record = self._context['onchange_self']
        eval_context.update({
            # orm
            'env': self.env,
            'model': model,
            # Exceptions
            'Warning': Warning,
            # record
            'record': record,
            'records': records,
            # helpers
            'log': log,
        })
        return eval_context

    def call_back(self, ch, method, properties, body):
        _logger.info(f"rabbitmq回调:{body}")
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))

            eval_context = self._get_eval_context(self)
            safe_eval(self.code.strip(), eval_context,
                      mode="exec", nocopy=True)
            new_cr.close()

    def get_client(self):
        """返回rabbitmq客户端"""
        try:
            credential = pika.PlainCredentials(self.user, self.password)
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.host, credentials=credential))
            channel = conn.channel(
                self.channel_number if self.channel_number else None)
            channel.exchange_declare(
                exchange=self.exchange, exchange_type=self.exchange_type)
            queue_name = self.queue_name if self.queue_name else ""
            result = channel.queue_declare(queue_name, exclusive=True)
            if not queue_name:
                self.queue_name = result.method.queue

            channel.queue_bind(exchange=self.exchange, queue=self.queue_name)
            channel.basic_consume(self.queue_name, self.call_back)
            return channel

        except Exception as err:
            _logger.error(f"创建RabbimtMq客户端失败:{traceback.format_exc()}")

    def test(self):
        _logger.info("回调方法成功运行>>>>>>>")

    def run(self):
        try:
            channel = self.get_client()
            self.state = 'running'
            _logger.info(f"运行rabbit server:{self.name}")
            t = threading.Thread(target=channel.start_consuming)
            t.setDaemon(True)
            t.start()
        except Exception as err:
            self.state = 'stopped'
            _logger.error(f"启动线程失败：{traceback.format_exc()}")
