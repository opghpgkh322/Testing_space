# Инициализационный файл для пакета widgets
# Этот файл делает папку widgets Python пакетом

from .base_tab import BaseTab
from .materials_tab import MaterialsTab
from .warehouse_tab import WarehouseTab
from .products_tab import ProductsTab
from .stages_tab import StagesTab
from .orders_tab import OrdersTab

__all__ = [
    'BaseTab',
    'MaterialsTab',
    'WarehouseTab',
    'ProductsTab',
    'StagesTab',
    'OrdersTab'
]