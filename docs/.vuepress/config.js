module.exports = {
  title: "KanadeBot",
  description: '一只可爱奏宝Bot的文档',
  dest: 'public',
  base: '/docs/',
  locales: {
    '/': {
      lang: 'zh-CN',
      recoLocales: {
        pagation: {
          prev: '上一页',
          next: '下一页',
          go: '前往',
          jump: '跳转至'
        }
      }
    }
  },
  head: [
    ['link', { rel: 'icon', href: '/image/icon.png' }],
    ['meta', { name: 'viewport', content: 'width=device-width,initial-scale=1,user-scalable=no' }]
  ],
  markdown: {
    lineNumbers: true
  },
  plugins: [
    ["sakura", {
      num: 10,  // 默认数量
      show: true, //  是否显示
      zIndex: -1,   // 层级
      img: {
        replace: true,  // false 默认图 true 换图 需要填写httpUrl地址
        httpUrl: '/docs/image/cup.png'     // 绝对路径
      }     
    }]
  ],
  theme: 'reco',
  themeConfig: {
    logo: '/image/head.png',
    nav: [
      { text: '主页', link: '/', icon: 'reco-home' },
      { text: '使用文档', link: '/use/', icon: 'reco-document' },
      { text: '关于Bot', link: '/about.md', icon: 'reco-faq' },
      { text: '更新日志', link: '/log/', icon: 'reco-date' },
    ],
    search: true,
    searchMaxSuggestions: 10,
    sidebar: {
      '/use/': [
        {
          title: '前言',
          path: '/use/'
        },
        {
          title: '通用插件',
          sidebarDepth: 1,
          children: [
          'common/pjsk',
          'common/relax', 
          'common/shop', 
          'common/tools',
          'common/info', 
          'common/genepic',
          'common/image', 
          'common/other',
          'common/webgame'
          ]
        },
        {
          title: '群管插件',
          path: 'admin/'
        },
        
        {
          title: '被动插件',
          path: 'passive/'
        },
      ]
    },
    lastUpdated: '最近更新于：',
    author: 'Yozora',
    subSidebar: 'auto',
    repo: 'cYanosora/kndbot',
    docsRepo: 'cYanosora/kndbot',
    docsDir: 'docs',
    docsBranch: 'main',
    editLinks: true,
    editLinkText: '对此有疑问?帮助改进文档'
  }
}  
