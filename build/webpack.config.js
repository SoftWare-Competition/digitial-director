var path = require('path')

module.exports = {
  mode: 'production',
  entry: './entry.js',
  output: {
    path: path.resolve(__dirname, '../miniprogram/lib/live2d'),
    filename: 'cubism4-bundle.js',
    libraryTarget: 'commonjs2'
  },
  target: 'node',
  externals: {
    '../../../lib/live2d/live2dcubismcore.min.js': 'commonjs ../../../lib/live2d/live2dcubismcore.min.js'
  },
  module: {
    rules: [{
      test: /\.js$/,
      exclude: /node_modules/,
      use: { loader: 'babel-loader', options: { presets: ['@babel/preset-env'] } }
    }]
  }
}
