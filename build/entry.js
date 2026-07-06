// 入口：为微信小程序导出 pixi-live2d-display
var PIXI = require('pixi.js')
var live2d = require('pixi-live2d-display')

// 注入 Cubism 4 Core
window.Live2DCubismCore = require('../miniprogram/lib/live2d/live2dcubismcore.min.js')

// 注册 cubism4 插件
live2d.Cubism4ModelMixin

module.exports = { PIXI: PIXI, Live2DModel: live2d.Live2DModel, Cubism4ModelMixin: live2d.Cubism4ModelMixin }
