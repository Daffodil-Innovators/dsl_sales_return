from odoo import api, models, fields, _
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class MultiApprovalTypeInherit(models.Model):
    _inherit = 'multi.approval.type'

    sales_return_id = fields.Many2one('sales.return', string='Sales Return')


class MultiApproval(models.Model):
    _inherit = 'multi.approval'

    def action_approve(self):
        recs = self.filtered(lambda x: x.state == 'Submitted')
        for rec in recs:
            if not rec.is_pic:
                msg = _('{} do not have the authority to approve this request!'.format(rec.env.user.name))
                self.sudo().message_post(body=msg)
                return False
            line = rec.line_id
            if not line or line.state != 'Waiting for Approval':
                # Something goes wrong!
                self.message_post(body=_('Something goes wrong!'))
                return False

            # Update follower
            rec.update_follower(self.env.uid)

            # check if this line is required
            other_lines = rec.line_ids.filtered(
                lambda x: x.sequence >= line.sequence and x.state == 'Draft')
            if not other_lines:
                rec.state = 'Approved'
                msg = _('I Approved')
            else:
                next_line = other_lines.sorted('sequence')[0]
                next_line.write({
                    'state': 'Waiting for Approval',
                })
                rec.line_id = next_line
                msg = _('I Recommended')
            line.state = 'Approved'
            # msg = _('I Approved')
            rec.message_post(body=msg)

            model = self.env['ir.model'].sudo().search([('model', '=', 'sales.return')], order='id desc', limit=1)
            if model:
                if rec.state == 'Draft':
                    sales_return = self.env['sales.return'].sudo().search([('approve_id', '=', rec.id)], order='id desc', limit=1)
                    if sales_return.state == 'assigned':
                            sales_return.state = 'completed'

              