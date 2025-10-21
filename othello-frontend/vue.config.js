const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  
  // *** 部署到 GitHub Pages 的关键配置 ***
  // 设置 Vue 应用的根路径，必须与你的 GitHub 仓库名称一致。
  // 注意：路径必须以斜杠 '/' 开头和结尾。
  publicPath: process.env.NODE_ENV === 'production'
    ? '/AlphaZero-Othello-web/' // 已更新为你的仓库名称
    : '/'
})
