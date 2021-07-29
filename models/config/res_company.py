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

import json
import logging
from pathlib import Path

import requests
from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    type_document_identification_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.type_document_identifications',
                                                      compute='_compute_edi',
                                                      inverse="_inverse_type_document_identification_id",
                                                      string="Tipo de documento de identificación")
    type_organization_id = fields.Many2one(comodel_name='l10n_co_edi_jorels.type_organizations', compute='_compute_edi',
                                           inverse="_inverse_type_organization_id", string="Tipo de organización")
    type_regime_id = fields.Many2one('l10n_co_edi_jorels.type_regimes', compute='_compute_edi',
                                     inverse="_inverse_type_regime_id", string="Tipo de regimen")
    type_liability_id = fields.Many2one('l10n_co_edi_jorels.type_liabilities', compute='_compute_edi',
                                        inverse="_inverse_type_liability_id", string="Tipo de responsabilidad")
    business_name = fields.Char(string="Razón social para facturar")
    merchant_registration = fields.Char(string="Registro mercantil", compute='_compute_merchant_registration',
                                        store=True)
    municipality_id = fields.Many2one('l10n_co_edi_jorels.municipalities', compute='_compute_edi',
                                      inverse="_inverse_municipality_id", string="Municipalidad")
    # trade_name = fields.Char(string="Nombre comercial", compute='_compute_edi')
    trade_name = fields.Char(related='partner_id.trade_name', store=True, readonly=False)

    # Electronic invoice sender Mail
    email_edi = fields.Char(related='partner_id.email_edi', store=True, readonly=False)
    email_edi_formatted = fields.Char('Formatted Email Edi', compute='_compute_email_edi_formatted',
                                      help='Format email edi address "Name <email_edi@domain>"')

    vat_formatted = fields.Char(string="Formatted Tax ID", compute="_compute_vat_formatted")

    # address -> street
    # phone -> phone
    # email -> email

    # Api key
    api_key = fields.Char(string="Api key")
    api_url = fields.Char(string="Api url", default='https://jorels.apifacturacionelectronica.xyz')

    # Software
    software_id = fields.Char(string="Software Id")
    software_pin = fields.Char(string="Pin")
    software_message = fields.Char(string="Ultimo mensaje")

    # Company Signature
    certificate_certificate = fields.Binary(string="Firma Digital")
    certificate_password = fields.Char(string="Contraseña")
    certificate_message = fields.Char(string="Ultimo mensaje")

    # Test
    is_not_test = fields.Boolean(string="Entorno de producción", default=False)
    test_set_id = fields.Char(string="TestSetId")
    enable_validate_state = fields.Boolean(string="Habilitar estado intermedio de Validación DIAN en la facturación",
                                           default=True)
    enable_mass_send_print = fields.Boolean(string="Email automatico de la factura al validar(En producción)",
                                            default=False)

    # Report
    report_custom_text = fields.Html(string="Header text")
    footer_custom_text = fields.Html(string="Footer text")

    ei_include_pdf_attachment = fields.Boolean(string="Include PDF attachment on electronic invoice email",
                                               default=True)

    def _compute_vat_formatted(self):
        for rec in self:
            type_document_identification_id = self.get_type_document_identification_id()
            if type_document_identification_id:
                if rec.vat:
                    identification_number_general = ''.join([i for i in rec.partner_id.vat if i.isdigit()])
                    # Si es Nit elimina el digito de verificación
                    if type_document_identification_id == 6:
                        rec.vat_formatted = identification_number_general[:-1]
                    else:
                        rec.vat_formatted = identification_number_general
                else:
                    rec.vat_formatted = ''
            else:
                rec.vat_formatted = ''

    @api.depends('name', 'email_edi')
    def _compute_email_edi_formatted(self):
        for partner in self:
            if partner.email_edi:
                partner.email_edi_formatted = tools.formataddr(
                    ((partner.name + ' - Facturación Electrónica') or u"False", partner.email_edi or u"False"))
            else:
                partner.email_edi_formatted = ''

    @api.multi
    def get_l10n_co_document_type(self):
        for rec in self.filtered(lambda company: company.partner_id):
            l10n_co_document_type = None
            if rec.type_document_identification_id.id:
                values = {
                    1: 'civil_registration',
                    2: 'id_card',
                    3: 'id_document',
                    4: 'residence_document',
                    5: 'foreign_id_card',
                    6: 'rut',
                    7: 'passport',
                    8: 'external_id',
                    9: 'external_id',
                    10: 'id_document'
                }
                l10n_co_document_type = values[rec.type_document_identification_id.id]

            return l10n_co_document_type

    @api.multi
    def get_company_type(self):
        for rec in self.filtered(lambda company: company.partner_id):
            company_type = None
            if rec.type_organization_id.id:
                values = {
                    1: 'company',
                    2: 'person'
                }
                company_type = values[rec.type_organization_id.id]

            return company_type

    @api.multi
    def get_type_document_identification_id(self):
        for rec in self:
            document_type = rec.partner_id.l10n_co_document_type
            if document_type:
                values = {
                    'civil_registration': 1,
                    'id_card': 2,
                    'id_document': 3,
                    'national_citizen_id': 3,
                    'residence_document': 4,
                    'foreign_id_card': 5,
                    'rut': 6,
                    'passport': 7,
                    'external_id': 8,
                    'diplomatic_card': 0,
                }
                document_type_id = values[document_type]
                if 1 <= document_type_id <= 8:
                    return document_type_id
            return None

    @api.multi
    def get_type_organization_id(self):
        for rec in self:
            company_type = rec.partner_id.company_type
            values = {
                'person': 2,
                'company': 1
            }
            return values[company_type]

    def _compute_edi(self):
        for company in self.filtered(lambda company: company.partner_id):
            type_document_identification_id = self.get_type_document_identification_id()
            type_organization_id = self.get_type_organization_id()
            type_regime_id = company.partner_id.type_regime_id
            type_liability_id = company.partner_id.type_liability_id
            municipality_id = company.partner_id.municipality_id
            company.update({
                'type_regime_id': type_regime_id,
                'type_liability_id': type_liability_id,
                'municipality_id': municipality_id,
                'type_document_identification_id': type_document_identification_id,
                'type_organization_id': type_organization_id
            })

    def _inverse_type_regime_id(self):
        for company in self:
            company.partner_id.type_regime_id = company.type_regime_id

    def _inverse_type_liability_id(self):
        for company in self:
            company.partner_id.type_liability_id = company.type_liability_id

    def _inverse_municipality_id(self):
        for company in self:
            company.partner_id.municipality_id = company.municipality_id

    def _inverse_type_document_identification_id(self):
        for company in self:
            company.partner_id.l10n_co_document_type = self.get_l10n_co_document_type()

    def _inverse_type_organization_id(self):
        for company in self:
            company.partner_id.company_type = self.get_company_type()

    # @api.multi
    # @api.depends('name')
    # def _compute_business_name(self):
    #     for rec in self:
    #         rec.business_name = rec.name

    @api.multi
    @api.depends('company_registry')
    def _compute_merchant_registration(self):
        for rec in self:
            rec.merchant_registration = rec.company_registry

    # Actualización de entorno
    @api.multi
    def update_environment(self, environment):
        for rec in self:
            success = False
            try:
                api_file_path = Path(__file__).parents[2] / 'static' / 'api.json'
                with open(api_file_path) as api_file:
                    requests_data = json.loads(api_file.read())
                requests_data['environment']['type_environment_id'] = environment
                _logger.debug("Request environment DIAN: %s",
                              json.dumps(requests_data['environment'], indent=2, sort_keys=False))

                token = rec.api_key
                api_url = rec.api_url

                header = {"accept": "application/json", "Content-Type": "application/json"}
                api_url = api_url + "/api/ubl2.1/config/environment"
                header.update({'Authorization': 'Bearer ' + token})
                response = requests.put(api_url, json.dumps(requests_data['environment']), headers=header).json()
                _logger.debug('API Response PUT environment: %s', response)

                if 'message' in response:
                    rec.env.user.notify_info(message=response['message'])

                response = requests.get(api_url, headers=header).json()
                _logger.debug('API Response GET environment: %s', response)

                if 'type_environment_id' in response:
                    if environment == response['type_environment_id']:
                        rec.env.user.notify_info(message="Se ha actualizado el entorno." \
                                                         "Ahora, sincronice las resoluciones")
                        success = True

                if 'message' in response:
                    rec.env.user.notify_info(message=response['message'])

            except Exception as e:
                _logger.debug("Error de comunicación: %s", e)

            return success

    @api.multi
    def write(self, vals):
        for rec in self:
            if 'is_not_test' in vals:
                if vals['is_not_test'] != rec.is_not_test:
                    if vals['is_not_test']:
                        environment = 1
                    else:
                        environment = 2

                    if not self.update_environment(environment):
                        vals['is_not_test'] = not vals['is_not_test']

        return super(ResCompany, self).write(vals)
