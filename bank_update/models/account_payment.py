# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class AccountPaymeny(models.Model):
    _inherit = "account.payment"

    x_destination_journal_id = fields.Many2one('account.journal', string='Transferir a',
                                               domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]", readonly=True,
                                               states={'draft': [('readonly', False)]})
    x_transfer_move = fields.Many2one(
        comodel_name='account.payment',
        string='Entrada de la transferencia', readonly=True, ondelete='cascade',
        check_company=True)

    def onchange_payment_type(self):
        if self.is_internal_transfer:
            self.payment_type = 'outbound'

    def action_post(self):
        res = super(AccountPaymeny, self).action_post()
        if self.is_internal_transfer and not self.x_transfer_move:
            paired_payment = self.copy(
                {
                    "journal_id": self.x_destination_journal_id.id,
                    "x_destination_journal_id": self.journal_id.id,
                    "payment_type": self.payment_type == "outbound"
                                    and "inbound"
                                    or "outbound",
                    "move_id": None,
                    "ref": self.ref,
                    "date":self.date,
                    "x_transfer_move": self.id,
                }
            )

            paired_payment.move_id._post(soft=False)
            
            # Agregado por petth_cash
            modulo = self.env['ir.module.module'].search([('name', '=', 'expense_petty_cash')])
            if modulo and modulo.state == 'installed':
                if paired_payment.is_petty_cash and paired_payment.petty_cash_id:
                    self.env['account.payment'].search([('id', '=', paired_payment.id)]).write({
                        'partner_id': paired_payment.petty_cash_id.partner_id.id,
                    })
                    self.env['account.move'].search([('id', '=', paired_payment.move_id.id)]).write({
                        'partner_id': paired_payment.petty_cash_id.partner_id.id,
                    })
                    self.env['account.move.line'].search([('move_id', '=', paired_payment.move_id.id)]).write({
                        'partner_id': paired_payment.petty_cash_id.partner_id.id,
                    })
            # << Agregado por petth_cash
            
            self.x_transfer_move = paired_payment
        return res
