from enum import StrEnum

from PyQt6.QtCore import QObject

class TabActionTypes(StrEnum):

    Unknown = ''

    Close = QObject.tr('Close')
    CloseAll = QObject.tr('Close All Tabs')
    CloseOther = QObject.tr('Close Other Tabs')
    CloseUnmodified = QObject.tr('Close Unmodified Tabs')
    CloseToLeft = QObject.tr('Close Tabs to the Left')
    CloseToRight = QObject.tr('Close Tabs to the Right')

