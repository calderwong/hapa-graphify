const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('hapaGraphifyDesktop', {
  shell: 'electron',
  protocol: 'hapa-graphify-desktop/0.1.0'
});
