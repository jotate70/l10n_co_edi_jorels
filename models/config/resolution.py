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

from odoo import api, fields, models
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)

try:
    import json
    import requests
    from pathlib import Path
except Exception as err:
    _logger.debug(err)


class Resolution(models.Model):
    _name = 'l10n_co_edi_jorels.resolution'
    _description = 'Electronic invoice resolution'
    _rec_name = 'name'

    name = fields.Char(string="Name", compute='_compute_name')

    resolution_api_sync = fields.Boolean(string="¿Sincronizar con la API?", default=True)

    # Range Resolution DIAN
    resolution_type_document_id = fields.Many2one(comodel_name="l10n_co_edi_jorels.type_documents",
                                                  string='Tipo de documento',
                                                  required=True, ondelete='RESTRICT')
    resolution_prefix = fields.Char(string="Prefijo")
    resolution_resolution = fields.Char(string="Resolución")
    resolution_resolution_date = fields.Date(string="Fecha de la resolución")
    resolution_technical_key = fields.Char(string="Llave tecnica")
    resolution_from = fields.Integer(string="Desde", required=True)
    resolution_to = fields.Integer(string="Hasta", required=True)
    resolution_date_from = fields.Date(string="Fecha Desde")
    resolution_date_to = fields.Date(string="Fecha Hasta")

    resolution_id = fields.Integer(string="Api ID", readonly=True, copy=False, index=True)
    resolution_number = fields.Integer(string="Numero", readonly=True, copy=False)
    resolution_next_consecutive = fields.Char(string="Siguiente consecutivo", readonly=True, copy=False)

    resolution_message = fields.Char(string="Mensaje", readonly=True)

    def _compute_name(self):
        for rec in self:
            rec.name = str(rec.resolution_id) + ' - ' + \
                       rec.resolution_type_document_id.name + ' [' + rec.resolution_type_document_id.code + ']'

    @api.model
    def create(self, vals):
        if vals['resolution_api_sync']:
            vals, success = self.post_resolution(vals)
            if success:
                return super(Resolution, self).create(vals)
            else:
                raise Warning("No se pudo guardar el registro en la API")
        else:
            return super(Resolution, self).create(vals)

    @api.multi
    def write(self, vals):
        for rec in self:
            if rec.resolution_api_sync:
                vals, success = self.put_resolution(vals)
                if success:
                    return super(Resolution, self).write(vals)
                else:
                    raise Warning("No se pudo actualizar el registro en la API")
            else:
                return super(Resolution, self).write(vals)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.resolution_api_sync:
                success = self.delete_resolution()
                if success:
                    return super(models.Model, self).unlink()
                else:
                    raise Warning("No se pudo eliminar el registro en la API")
            else:
                return super(models.Model, self).unlink()

    # Creación de resolución
    @api.multi
    def post_resolution(self, vals):
        success = False
        try:
            api_file_path = Path(__file__).parents[2] / 'static' / 'api.json'
            with open(api_file_path) as api_file:
                requests_data = json.loads(api_file.read())

            requests_data['resolucion']['type_document_id'] = vals['resolution_type_document_id']

            if vals['resolution_prefix']:
                requests_data['resolucion']['prefix'] = vals['resolution_prefix']
            else:
                del requests_data['resolucion']['prefix']

            if vals['resolution_resolution']:
                requests_data['resolucion']['resolution'] = vals['resolution_resolution']
            else:
                del requests_data['resolucion']['resolution']

            if vals['resolution_resolution_date']:
                requests_data['resolucion']['resolution_date'] = vals['resolution_resolution_date']
            else:
                del requests_data['resolucion']['resolution_date']

            if vals['resolution_technical_key']:
                requests_data['resolucion']['technical_key'] = vals['resolution_technical_key']
            else:
                del requests_data['resolucion']['technical_key']

            requests_data['resolucion']['from'] = vals['resolution_from']
            requests_data['resolucion']['to'] = vals['resolution_to']

            if vals['resolution_date_from']:
                requests_data['resolucion']['date_from'] = vals['resolution_date_from']
            else:
                del requests_data['resolucion']['date_from']

            if vals['resolution_date_to']:
                requests_data['resolucion']['date_to'] = vals['resolution_date_to']
            else:
                del requests_data['resolucion']['date_to']

            _logger.debug("Request create resolution DIAN: %s",
                          json.dumps(requests_data['resolucion'], indent=2, sort_keys=False))

            token = str(self.env.user.company_id.api_key)
            api_url = str(self.env.user.company_id.api_url)

            header = {"accept": "application/json", "Content-Type": "application/json"}
            api_url = api_url + "/api/ubl2.1/config/resolution"
            header.update({'Authorization': 'Bearer' + ' ' + token})
            response = requests.post(api_url, json.dumps(requests_data['resolucion']), headers=header).json()
            _logger.debug('API Response: %s', response)

            if 'resolution' in response:
                vals['resolution_id'] = response['resolution']['id']
                vals['resolution_number'] = response['resolution']['number']
                vals['resolution_next_consecutive'] = response['resolution']['next_consecutive']
                success = True

            if 'message' in response:
                if response['message'] == 'Unauthenticated.':
                    vals['resolution_message'] = 'No es posible la autenticación con la API. ' \
                                                 'Revise su Api key e intente nuevamente.'
                else:
                    vals['resolution_message'] = response['message']
            else:
                vals['resolution_message'] = 'Algo sucede. No es posible comunicarse con la API'
        except Exception as e:
            vals['resolution_message'] = "¡Error de conexión con la API!"
            _logger.debug("Error de conexión: %s", e)
        return vals, success

    # Actualización de resolución
    @api.multi
    def put_resolution(self, vals):
        success = False
        for rec in self:
            try:
                api_file_path = Path(__file__).parents[2] / 'static' / 'api.json'
                with open(api_file_path) as api_file:
                    requests_data = json.loads(api_file.read())

                # Resolution api id for update
                resolution_id = str(rec.resolution_id)

                requests_data['resolucion']['type_document_id'] = rec.resolution_type_document_id.id
                requests_data['resolucion']['prefix'] = rec.resolution_prefix
                requests_data['resolucion']['resolution'] = rec.resolution_resolution
                requests_data['resolucion']['resolution_date'] = fields.Date.to_string(rec.resolution_resolution_date)
                requests_data['resolucion']['technical_key'] = rec.resolution_technical_key
                requests_data['resolucion']['from'] = rec.resolution_from
                requests_data['resolucion']['to'] = rec.resolution_to
                requests_data['resolucion']['date_from'] = fields.Date.to_string(rec.resolution_date_from)
                requests_data['resolucion']['date_to'] = fields.Date.to_string(rec.resolution_date_to)

                len_prefix = len('resolution_')
                for val in vals:
                    requests_data['resolucion'][val[len_prefix:]] = vals[val]

                if not requests_data['resolucion']['prefix']:
                    requests_data['resolucion']['prefix'] = ''

                if not requests_data['resolucion']['resolution']:
                    requests_data['resolucion']['resolution'] = ''

                if not requests_data['resolucion']['resolution_date']:
                    requests_data['resolucion']['resolution_date'] = ''

                if not requests_data['resolucion']['technical_key']:
                    requests_data['resolucion']['technical_key'] = ''

                if not requests_data['resolucion']['date_from']:
                    requests_data['resolucion']['date_from'] = ''

                if not requests_data['resolucion']['date_to']:
                    requests_data['resolucion']['date_to'] = ''

                _logger.debug("Request update resolution DIAN: %s",
                              json.dumps(requests_data['resolucion'], indent=2, sort_keys=False))

                token = str(self.env.user.company_id.api_key)
                api_url = str(self.env.user.company_id.api_url)

                header = {"accept": "application/json", "Content-Type": "application/json"}
                api_url = api_url + "/api/ubl2.1/config/resolution/" + resolution_id
                header.update({'Authorization': 'Bearer' + ' ' + token})
                response = requests.put(api_url, json.dumps(requests_data['resolucion']), headers=header).json()
                _logger.debug('API Response: %s', response)

                if 'resolution' in response:
                    # vals['resolution_id'] = response['resolution']['id']
                    vals['resolution_number'] = response['resolution']['number']
                    vals['resolution_next_consecutive'] = response['resolution']['next_consecutive']
                    success = True

                if 'message' in response:
                    if response['message'] == 'Unauthenticated.':
                        vals['resolution_message'] = 'No es posible la autenticación con la API. ' \
                                                     'Revise su Api key e intente nuevamente.'
                    else:
                        vals['resolution_message'] = response['message']
                else:
                    vals['resolution_message'] = 'Algo sucede. No es posible comunicarse con la API'
            except Exception as e:
                vals['resolution_message'] = "¡Error de conexión con la API!"
                _logger.debug("Error de conexión: %s", e)
        return vals, success

    # Eliminación de resolución
    @api.multi
    def delete_resolution(self):
        success = False
        for rec in self:
            try:
                # Resolution api id for update
                resolution_id = str(rec.resolution_id)

                # The function str() is necessary for 'False' answers and boolean exceptions
                token = str(self.env.user.company_id.api_key)
                api_url = str(self.env.user.company_id.api_url)

                header = {"accept": "application/json", "Content-Type": "application/json"}
                api_url = api_url + "/api/ubl2.1/config/resolution/" + str(resolution_id)
                header.update({'Authorization': 'Bearer' + ' ' + token})
                response = requests.delete(api_url, headers=header).json()
                _logger.debug('API Response: %s', response)

                if 'message' in response:
                    if response['message'] == 'Unauthenticated.':
                        rec.resolution_message = 'No es posible la autenticación con la API. ' \
                                                 'Revise su Api key e intente nuevamente.'
                    elif response['message'] == 'Resolución eliminada con éxito':
                        success = True
                    else:
                        rec.resolution_message = response['message']
                else:
                    rec.resolution_message = 'Algo sucede. No es posible comunicarse con la API'
            except Exception as e:
                rec.resolution_message = '¡Error de conexión con la API!'
                _logger.debug("Error de conexión: %s", e)
                raise Warning(rec.resolution_message)
        return success
