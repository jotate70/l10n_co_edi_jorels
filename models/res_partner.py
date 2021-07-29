# -*- coding: utf-8 -*-
#
# Jorels S.A.S. - Copyright (2019-2021)
#
# This file is part of l10n_co_edi_jorels.
#
# l10n_co_edi_jorels is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# l10n_co_edi_jorels is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with l10n_co_edi_jorels.  If not, see <https://www.gnu.org/licenses/>.
#
# email: info@jorels.com
#

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    type_regime_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.type_regimes', string="Tipo de regimen",
                                     ondelete='RESTRICT')
    type_liability_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.type_liabilities',
                                        string="Tipo de responsabilidad", ondelete='RESTRICT')
    merchant_registration = fields.Char(string="Registro mercantil")
    municipality_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.municipalities', string="Municipalidad",
                                      ondelete='RESTRICT')
    email_edi = fields.Char("Email para facturación")

    trade_name = fields.Char(string="Nombre comercial", copy=False)

    customer_software_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.customer_software',
                                           string="Customer software", copy=False, ondelete='RESTRICT')
