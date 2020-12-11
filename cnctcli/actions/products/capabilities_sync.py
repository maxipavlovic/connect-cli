from collections import namedtuple

from tqdm import trange

from cnctcli.actions.products.sync import ProductSynchronizer
from cnctcli.actions.products.constants import (
    CAPABILITIES,
    DEFAULT_BAR_FORMAT,
)

from cnctcli.actions.products.utils import cleanup_product_for_update
from cnctcli.actions.products.constants import CAPABILITIES_COLS_HEADERS

fields = (v.replace(' ', '_').lower() for v in CAPABILITIES_COLS_HEADERS.values())

_RowData = namedtuple('RowData', fields)


class CapabilitiesSynchronizer(ProductSynchronizer):
    def sync(self):
        ws = self._wb['Capabilities']
        errors = {}
        skipped_count = 0
        updated_items = []

        row_indexes = trange(
            2, ws.max_row + 1, disable=self._silent, leave=True, bar_format=DEFAULT_BAR_FORMAT
        )
        for row_idx in row_indexes:
            data = _RowData(*[ws.cell(row_idx, col_idx).value for col_idx in range(1, 4)])
            row_indexes.set_description(f'Processing Product capabilities {data.capability}')
            if data.action == '-':
                skipped_count += 1
                continue
            row_errors = self._validate_row(data)

            if row_errors:
                errors[row_idx] = row_errors
                continue

            product = cleanup_product_for_update(self._client.products[self._product_id].get())

            if data.action == 'update':
                update = True
                try:
                    if data.capability == 'Pay-as-you-go support and schema':
                        if data.value != 'Disabled':
                            if not product['capabilities']['ppu']:
                                product['capabilities']['ppu'] = {
                                    'schema': data.value,
                                    'dynamic': False,
                                    'future': False
                                }
                            else:
                                product['capabilities']['ppu']['schema'] = data.value
                        else:
                            product['capabilities']['ppu'] = None
                    if data.capability == 'Pay-as-you-go dynamic items support':
                        if not product['capabilities']['ppu']:
                            if data.value == 'Enabled':
                                raise Exception(
                                    "Dynamic items support can't be enabled without Pay-as-you-go "
                                    "support"
                                )
                            update = False
                        else:
                            if data.value == 'Enabled':
                                product['capabilities']['ppu']['dynamic'] = True
                            else:
                                product['capabilities']['ppu']['dynamic'] = False
                    if data.capability == "Pay-as-you-go future charges support":
                        if not product['capabilities']['ppu']:
                            if data.value == 'Enabled':
                                raise Exception(
                                    "Report of future charges can't be enabled without Pay-as-you-go "
                                    "support"
                                )
                            update = False

                        else:
                            if data.value == 'Enabled':
                                product['capabilities']['ppu']['future'] = True
                            else:
                                product['capabilities']['ppu']['future'] = False
                    if data.capability == 'Consumption reporting for Reservation Items':
                        if data.value == 'Enabled':
                            product['capabilities']['reservation']['consumption'] = True
                        else:
                            product['capabilities']['reservation']['consumption'] = False

                    if data.capability == 'Dynamic Validation of the Draft Requests':
                        if data.value == 'Enabled':
                            product['capabilities']['cart']['validation'] = True
                        else:
                            product['capabilities']['cart']['validation'] = False

                    if data.capability == 'Dynamic Validation of the Inquiring Form':
                        if data.value == 'Enabled':
                            product['capabilities']['inquiring']['validation'] = True
                        else:
                            product['capabilities']['inquiring']['validation'] = False

                    if data.capability == 'Reseller Authorization Level':
                        if data.value == 'Disabled':
                            product['capabilities']['tiers']['configs'] = None
                        else:
                            product['capabilities']['tiers']['configs'] = {
                                'level': data.value
                            }
                    if data.capability == 'Tier Accounts Sync':
                        if data.value == 'Enabled':
                            product['capabilities']['tiers']['updates'] = True
                        else:
                            product['capabilities']['tiers']['updates'] = False
                    if data.capability == 'Administrative Hold':
                        if data.value == 'Enabled':
                            product['capabilities']['subscription']['hold'] = True
                        else:
                            product['capabilities']['subscription']['hold'] = False
                    if update:
                        self._client.products[self._product_id].update(product)
                    updated_items.append(data.capability)

                except Exception as e:
                    errors[row_idx] = [str(e)]

        return (
            skipped_count,
            len(updated_items),
            errors,
        )

    @staticmethod
    def _validate_row(data):
        errors = []
        if data.capability not in CAPABILITIES:
            errors.append(
                f'Capability {data.capability} is not valid capability'
            )
        if data.capability == 'Pay-as-you-go support and schema':
            if data.value not in (
                'Disabled', 'QT', 'TR', 'PR', 'CR'
            ):
                errors.append(f'Schema {data.value} is not supported')
            return errors
        if data.capability == 'Reseller Authorization Level' and data.value not in (
            'Disabled', 1, 2
        ):
            errors.append(f'{data.value } is not valid for Reseller Authorization level capability')
            return errors
        if data.value not in ('Disabled', 'Enabled') and data.capability != 'Reseller ' \
                                                                            'Authorization Level':
            errors.append(f'{data.capability} may be Enabled or Disabled, but not {data.value}')
        return errors