// 全局时间格式化工具 - 确保使用北京时间
export const formatTime = (dateStr, format = '%Y-%m-%d %H:%M:%S') => {
  if (!dateStr) return ''
  
  // 解析日期字符串
  let date
  if (typeof dateStr === 'string') {
    // 处理 ISO 格式字符串，确保正确解析
    if (dateStr.includes('T')) {
      // 如果是 ISO 格式，直接创建 Date 对象
      date = new Date(dateStr)
    } else {
      // 其他格式尝试直接解析
      date = new Date(dateStr)
    }
  } else if (dateStr instanceof Date) {
    date = dateStr
  } else {
    return ''
  }
  
  // 检查日期是否有效
  if (isNaN(date.getTime())) {
    return ''
  }
  
  // 使用本地时间（北京时间）获取各个部分
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')

  return format
    .replace('%Y', year)
    .replace('%m', month)
    .replace('%d', day)
    .replace('%H', hour)
    .replace('%M', minute)
    .replace('%S', second)
}