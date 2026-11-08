# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'gui_pathfinder.ui'
##
## Created by: Qt User Interface Compiler version 6.9.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QGridLayout, QLabel, QLineEdit, QSizePolicy,
    QWidget)
from . import resources_rc

class Ui_PathfinderDialog(object):
    def setupUi(self, PathfinderDialog):
        if not PathfinderDialog.objectName():
            PathfinderDialog.setObjectName(u"PathfinderDialog")
        PathfinderDialog.resize(480, 220)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(PathfinderDialog.sizePolicy().hasHeightForWidth())
        PathfinderDialog.setSizePolicy(sizePolicy)
        PathfinderDialog.setMinimumSize(QSize(480, 220))
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(9)
        PathfinderDialog.setFont(font)
        icon = QIcon()
        icon.addFile(u":/images/app_icon.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        PathfinderDialog.setWindowIcon(icon)
        PathfinderDialog.setSizeGripEnabled(False)
        self.gridLayout = QGridLayout(PathfinderDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_name = QLabel(PathfinderDialog)
        self.label_name.setObjectName(u"label_name")
        self.label_name.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label_name, 0, 0, 1, 1)

        self.lineEdit_name = QLineEdit(PathfinderDialog)
        self.lineEdit_name.setObjectName(u"lineEdit_name")

        self.gridLayout.addWidget(self.lineEdit_name, 0, 1, 1, 1)

        self.label_url = QLabel(PathfinderDialog)
        self.label_url.setObjectName(u"label_url")
        self.label_url.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label_url, 1, 0, 1, 1)

        self.lineEdit_url = QLineEdit(PathfinderDialog)
        self.lineEdit_url.setObjectName(u"lineEdit_url")

        self.gridLayout.addWidget(self.lineEdit_url, 1, 1, 1, 1)

        self.label_token = QLabel(PathfinderDialog)
        self.label_token.setObjectName(u"label_token")
        self.label_token.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label_token, 2, 0, 1, 1)

        self.lineEdit_token = QLineEdit(PathfinderDialog)
        self.lineEdit_token.setObjectName(u"lineEdit_token")
        self.lineEdit_token.setInputMethodHints(Qt.ImhHiddenText|Qt.ImhNoAutoUppercase|Qt.ImhNoPredictiveText|Qt.ImhSensitiveData)
        self.lineEdit_token.setEchoMode(QLineEdit.Password)

        self.gridLayout.addWidget(self.lineEdit_token, 2, 1, 1, 1)

        self.label_help = QLabel(PathfinderDialog)
        self.label_help.setObjectName(u"label_help")
        self.label_help.setWordWrap(True)
        self.label_help.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label_help, 3, 1, 1, 1)

        self.buttonBox = QDialogButtonBox(PathfinderDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.gridLayout.addWidget(self.buttonBox, 4, 0, 1, 2)


        self.retranslateUi(PathfinderDialog)
        self.buttonBox.accepted.connect(PathfinderDialog.accept)
        self.buttonBox.rejected.connect(PathfinderDialog.reject)

        QMetaObject.connectSlotsByName(PathfinderDialog)
    # setupUi

    def retranslateUi(self, PathfinderDialog):
        PathfinderDialog.setWindowTitle(QCoreApplication.translate("PathfinderDialog", u"Pathfinder Configuration", None))
        self.label_name.setText(QCoreApplication.translate("PathfinderDialog", u"Name:", None))
        self.label_url.setText(QCoreApplication.translate("PathfinderDialog", u"URL:", None))
        self.lineEdit_url.setPlaceholderText(QCoreApplication.translate("PathfinderDialog", u"https://your-pathfinder-instance or a JSON export URL", None))
        self.label_token.setText(QCoreApplication.translate("PathfinderDialog", u"API token:", None))
        self.lineEdit_token.setPlaceholderText(QCoreApplication.translate("PathfinderDialog", u"Optional", None))
        self.label_help.setText(QCoreApplication.translate("PathfinderDialog", u"<html><head/><body><p>Points at a Pathfinder JSON connections export (a URL ending in .json, an /api path, or a base URL serving /api/connections).</p></body></html>", None))
    # retranslateUi

