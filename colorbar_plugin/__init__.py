def classFactory(iface):
    from .colorbar_plugin import ColorbarExporter
    return ColorbarExporter(iface)