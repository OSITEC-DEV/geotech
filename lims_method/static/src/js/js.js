odoo.define('lims_pos.ClientDetailsEdit', function (require) {
    'use strict';
    const models = require('point_of_sale.models');
    models.load_fields('res.partner', ['passport_no','partner_no','gender','age','blood_group']);

    var screen = require('point_of_sale.ClientDetailsEdit')
    /*console.log("Helloooooo")*/

});
