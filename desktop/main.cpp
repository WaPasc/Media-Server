#include <QApplication>
#include <QMainWindow>
#include <QLabel>
#include <QVBoxLayout>
#include <QWidget>

int main(int argc, char *argv[]) {
    // 1. Initialize the Qt Application
    QApplication app(argc, argv);

    // 2. Create the main window
    QMainWindow mainWindow;
    mainWindow.setWindowTitle("Media Server");
    mainWindow.resize(1280, 720);

    // 3. Create a central widget and layout
    QWidget *centralWidget = new QWidget(&mainWindow);
    QVBoxLayout *layout = new QVBoxLayout(centralWidget);

    // 4. Add some temporary text where our video player will eventually go
    QLabel *label = new QLabel("QT app is initialized", centralWidget);
    label->setAlignment(Qt::AlignCenter);
    
    // Font and color
    QFont font = label->font();
    font.setPointSize(24);
    font.setBold(true);
    label->setFont(font);
    label->setStyleSheet("color: #000000;");

    layout->addWidget(label);
    mainWindow.setCentralWidget(centralWidget);

    // 5. Show the window and start the application loop
    mainWindow.show();
    return app.exec();
}