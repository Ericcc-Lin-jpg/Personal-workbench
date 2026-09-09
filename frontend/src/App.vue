<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import './chat-viewer.css'
import './chat-upload.css'
import './chat-groups.css'
import './theme.css'
import {
  Bell, Bookmark, CalendarDays, Check, ChevronDown, ChevronLeft, ChevronRight, CircleDot, Clock3, Filter,
  Ellipsis, FileText, GraduationCap, Heart, ImagePlus, LayoutDashboard, ListTodo, MapPin, Menu, MessageCircle, Mic, Paperclip, Pencil, Plus, Search,
  Settings2, Sparkles, Square, Trophy, Trash2, UserPlus, UserRound, UsersRound, X,
} from '@lucide/vue'

const activeView = ref('首页')
const homeFeedTab = ref('为你推荐')
const homeComposerOpen = ref(false)
const homeComposerDraft = ref('')
const homeLikedPostIds = ref([])
const homeSavedPostIds = ref([])
const homeFollowedUserIds = ref([])
const homeJoinedGroupIds = ref([])
const communityPosts = ref([
  {
    id: 1,
    author: '周予安',
    initials: '周',
    school: '广州某国际学校',
    grade: 'G12',
    time: '18 分钟前',
    scope: '华南地区',
    title: '申请季开始后，大家是怎么安排文书和标化的？',
    body: '最近同时准备托福和早申文书，有点不知道先做哪一件。想听听同样在申请季的同学怎么拆分每周任务。',
    tags: ['大学申请', '时间规划'],
    likes: 24,
    comments: 8,
    liked: false,
    saved: false,
    followed: false,
    verified: false,
  },
  {
    id: 2,
    author: '陈老师',
    initials: '陈',
    school: '升学指导',
    grade: '认证顾问',
    time: '1 小时前',
    scope: '申请季',
    title: '9 月申请季提醒：先确认推荐信和成绩单流程',
    body: '很多学校的推荐信需要提前预留时间。建议本周完成推荐人沟通，并把每所大学的材料要求放进自己的申请时间线。',
    tags: ['申请提醒', '经验分享'],
    likes: 41,
    comments: 12,
    liked: false,
    saved: false,
    followed: false,
    verified: true,
  },
  {
    id: 3,
    author: '林子晴',
    initials: '林',
    school: '深圳国际交流中心',
    grade: 'G11',
    time: '昨天',
    scope: '竞赛交流',
    title: '寻找一起参加 HOSA 的队友',
    body: '目前有两位同学，想找熟悉生物或医学方向的同学一起准备。线上协作即可，希望是华南地区、时间比较稳定的伙伴。',
    tags: ['竞赛组队', 'HOSA'],
    likes: 17,
    comments: 5,
    saved: false,
    liked: false,
    followed: false,
    verified: false,
  },
])
const communityGroups = ref([
  { id: 1, name: '华南国际生申请季', meta: '1,284 位成员', icon: '🎓', tone: 'blue', joined: true },
  { id: 2, name: 'AP 微积分互助', meta: '326 位成员 · 本周 18 条讨论', icon: '📘', tone: 'green', joined: false },
  { id: 3, name: '国际生竞赛组队站', meta: '764 位成员', icon: '🏆', tone: 'orange', joined: false },
])
const communityEvents = ref([
  { id: 1, title: '华南国际生申请经验分享会', date: '9月7日 周一', place: '线上 · 20:00', type: '讲座', joined: false },
  { id: 2, title: '跨校 SAT 备考小组招募', date: '9月10日 周四', place: '线上协作', type: '学习小组', joined: true },
  { id: 3, title: 'HOSA 竞赛队友匹配', date: '9月14日 周一', place: '广州 · 深圳', type: '竞赛', joined: false },
])
const personalSpaceTab = ref('动态')
const personalSpaceVisibility = ref('交流圈可见')
const friendTab = ref('我的好友')
const friendQuery = ref('')
const friendProfile = ref(null)
const friendsLoading = ref(false)
const friendsError = ref('')
const friendUsers = ref([
  { id: 'demo-1', name: '周予安', initials: '周', school: '广州某国际学校', grade: 'G12', bio: '申请季一起拆解任务', status: 'friend', mutual: 4, online: true },
  { id: 'demo-2', name: '林子晴', initials: '林', school: '深圳国际交流中心', grade: 'G11', bio: '正在寻找竞赛队友', status: 'friend', mutual: 2, online: false },
  { id: 'demo-3', name: '陈老师', initials: '陈', school: '升学指导', grade: '认证顾问', bio: '帮助国际学生规划申请路径', status: 'not_friend', mutual: 0, online: true, verified: true },
  { id: 'demo-4', name: '许嘉禾', initials: '许', school: '佛山国际学校', grade: 'G12', bio: 'AP 微积分和 SAT 备考中', status: 'pending_received', mutual: 3, online: true },
  { id: 'demo-5', name: '沈知行', initials: '沈', school: '珠海国际学校', grade: 'G11', bio: '喜欢研究学校申请要求', status: 'pending_sent', mutual: 1, online: false },
  { id: 'demo-6', name: '梁思远', initials: '梁', school: '广州外国语学校', grade: 'G12', bio: '寻找一起做项目的伙伴', status: 'not_friend', mutual: 2, online: false },
])
const chatQuery = ref('')
const chatMode = ref('private')
const chatPeer = ref(null)
const chatGroup = ref(null)
const chatDraft = ref('')
const chatGroupDraft = ref('')
const chatGroups = ref([])
const chatGroupLoading = ref(false)
const chatGroupMessagesLoading = ref(false)
const chatGroupFormOpen = ref(false)
const newChatGroup = ref({ name: '', kind: 'learning', description: '' })
const chatGroupInvitations = ref([])
const chatGroupInviteOpen = ref(false)
const chatGroupInviteLoading = ref(false)
const chatGroupInviteError = ref('')
const chatGroupInviteCandidates = ref([])
const chatGroupPendingInvitations = ref([])
const chatGroupInviteSendingIds = ref([])
const chatGroupMessages = ref([])
const chatGroupMessagesRef = ref(null)
const chatGroupImageInputRef = ref(null)
const chatGroupImageFile = ref(null)
const chatGroupImagePreview = ref('')
const chatGroupAttachmentInputRef = ref(null)
const chatGroupAttachmentFile = ref(null)
const chatGroupAttachment = ref(null)
const chatGroupSharedTask = ref(null)
const chatGroupTaskPickerOpen = ref(false)
const chatGroupSending = ref(false)
const chatGroupUploadState = ref('idle')
const chatGroupUploadProgress = ref(0)
const chatMessageQuery = ref('')
const chatMessageSearchOpen = ref(false)
const chatMessageActionId = ref(null)
const chatHiddenMessageIds = ref([])
const chatTaskPickerOpen = ref(false)
const chatSharedTask = ref(null)
const chatImageInputRef = ref(null)
const chatImageFile = ref(null)
const chatImagePreview = ref('')
const chatAttachmentInputRef = ref(null)
const chatAttachmentFile = ref(null)
const chatAttachment = ref(null)
const chatRecording = ref(false)
const chatRecordingSeconds = ref(0)
const chatRecordingError = ref('')
const chatImageViewer = ref('')
const chatImageDropActive = ref(false)
const chatUploadState = ref('idle')
const chatUploadProgress = ref(0)
const chatMessages = ref([])
const chatMessagesRef = ref(null)
const chatsLoading = ref(false)
const chatMessagesLoading = ref(false)
const chatSending = ref(false)
const chatError = ref('')
const chats = ref([
  {
    id: 'demo-chat-1',
    userId: 'demo-1',
    name: '周予安',
    initials: '周',
    school: '广州某国际学校',
    grade: 'G12',
    online: true,
    unread: 2,
    lastMessage: '我整理了一份申请季任务拆分，晚点发给你。',
    lastAt: '昨天',
  },
  {
    id: 'demo-chat-2',
    userId: 'demo-2',
    name: '林子晴',
    initials: '林',
    school: '深圳国际交流中心',
    grade: 'G11',
    online: false,
    unread: 0,
    lastMessage: 'HOSA 队友的事情可以继续聊。',
    lastAt: '周一',
  },
])
const demoChatMessages = ref({
  'demo-1': [
    { id: 'demo-message-1', senderId: 'demo-1', senderName: '周予安', content: '最近申请季任务有点多，你也在整理时间表吗？', time: '昨天 20:12', isMine: false, read: true },
    { id: 'demo-message-2', senderId: 'me', senderName: '我', content: '对，我刚把文书和标化拆开了。', time: '昨天 20:16', isMine: true, read: true },
    { id: 'demo-message-3', senderId: 'demo-1', senderName: '周予安', content: '我整理了一份申请季任务拆分，晚点发给你。', time: '昨天 20:18', isMine: false, read: false },
  ],
  'demo-2': [
    { id: 'demo-message-4', senderId: 'demo-2', senderName: '林子晴', content: 'HOSA 队友的事情可以继续聊。', time: '周一 18:42', isMine: false, read: true },
  ],
})
const timelineView = ref('时间轴')
const calendarMode = ref('月')
const selectedDate = ref('2026-08-31')
const calendarCursor = ref('2026-08-31')
const selectedTask = ref(null)
const taskEditorOpen = ref(false)
const taskEditor = ref({ status: 'todo', priority: 'normal', note: '', reminders: [], planDate: '', plannedStart: '', plannedEnd: '' })
const taskEditorEndsAtMidnight = ref(false)
const taskEditorError = ref('')
const taskEditorSaving = ref(false)
const isAuthenticated = ref(false)
const authMode = ref('login')
const authRole = ref('student')
const authLoading = ref(false)
const authError = ref('')
const authMessage = ref('')
const passwordResetForm = ref({ email: '', uid: '', token: '', newPassword: '' })
const schoolOptions = ref([])
const demoAvailable = ref(true)
const demoAccount = ref({ email: 'student@demo.local', password: 'demo123456' })
const teacherDemoAccount = ref({ email: 'teacher.demo@ddl.local', password: 'Teacher2026!' })
const authForm = ref({ name: '', email: '', password: '', schoolId: '', termId: '' })
const showCreate = ref(false)
const draggingTask = ref(null)
const dragOverZone = ref('')
const timelineDragMinutes = ref(null)
const timelineBoardRef = ref(null)
const todoPanelRef = ref(null)
const urgentDropZoneRef = ref(null)
const completedDropZoneRef = ref(null)
const pointerDrag = ref(null)
const timelineDragDraft = ref(null)
const suppressTaskClick = ref(false)
let suppressClickTimer
const resizingTask = ref(null)
const resizeDraft = ref(null)
let resizePointerId = null
let resizeMoveFrame
let pendingResizeClientY = null
let resizeSession = null
let timelineElementPreview = null
const timelineError = ref('')
let timelineAutoScrollFrame
let timelinePointerClientY = null
let pointerDragFrame
let pendingPointerDragPosition = null
let pageAutoScrollFrame
let pagePointerClientX = null
let pagePointerClientY = null
let pointerDropGeometries = null
const pageAutoScrollEdge = 90
const timelineHourHeight = 96
const timelineHeaderHeight = 46
const timelineCanvasHeight = timelineHeaderHeight + (24 * timelineHourHeight) + 24
const timelineMinimumVisualDuration = (60 / timelineHourHeight) * 60
const timelinePointVisualPadding = (28 / timelineHourHeight) * 30
const timelineHourMarks = Array.from({ length: 25 }, (_, hour) => ({
  hour,
  label: `${String(hour).padStart(2, '0')}:00`,
}))
const filter = ref('我的课程')
const query = ref('')
const newTask = ref({ title: '', due: '2026-08-31', dueTime: '23:59', note: '' })
const editingPersonalTask = ref(null)
const tasks = ref([])
const subscriptions = ref([])
const dashboard = ref({
  identity: {},
  today: { date: '', total: 0, completed: 0, percent: 0, urgent: 0, tasks: [] },
  week: { start: '', end: '', total: 0, tasks: [] },
  checkin: { checkedIn: false, streak: 0, completedAt: null, recent: [] },
})
const dashboardLoading = ref(false)
const dashboardError = ref('')
const showAllWeekTasks = ref(false)
const dashboardIdentityExpanded = ref(false)
const dashboardProgressExpanded = ref(false)
const dashboardCheckinExpanded = ref(false)
const dashboardTodayGridRef = ref(null)
const nowTick = ref(Date.now())
let countdownTimer
let syncTimer
let dashboardRefreshTimer
let chatRefreshTimer
let chatSocket = null
let chatSocketPeerId = null
let chatSocketReconnectTimer
let chatGroupSocket = null
let chatGroupSocketId = null
let chatGroupSocketReconnectTimer
let chatRecorder = null
let chatRecorderStream = null
let chatRecorderChunks = []
let chatRecordingTimer
const annualPlanYear = ref(2026)
const annualPlanZoom = ref(12)
const annualPlanStartMonth = ref(0)
const annualPlanTasks = ref([])
const annualPlanLoading = ref(false)
const annualPlanError = ref('')
const annualPlanEditorOpen = ref(false)
const annualPlanDetail = ref(null)
const editingAnnualPlanTask = ref(null)
const annualPlanDeletePending = ref(null)
const annualPlanSaving = ref(false)
const annualPlanDeleting = ref(false)
const editingAnnualPlanSubtaskId = ref(null)
const annualPlanSubtaskDraft = ref({ title: '', dueDate: '' })
const annualPlanSubtaskEdit = ref({ title: '', dueDate: '' })
const annualPlanForm = ref({
  category: 'application',
  type: 'period',
  title: '',
  startDate: '',
  endDate: '',
  nodeDate: '',
  description: '',
})
const annualCategories = [
  { id: 'academic', label: '学术', icon: '📘', color: '#5f91bd' },
  { id: 'test', label: '标化', icon: '📗', color: '#6e9b79' },
  { id: 'competition', label: '竞赛', icon: '📕', color: '#c97958' },
  { id: 'application', label: '申请', icon: '📙', color: '#8b75b8' },
  { id: 'personal', label: '个人', icon: '📒', color: '#c58a43' },
]
const visibleAnnualCategories = ref(annualCategories.map((category) => category.id))
const notifications = ref([])
const showNotifications = ref(false)
const notificationLoading = ref(false)
const showGlobalSearch = ref(false)
const globalQuery = ref('')
const showSettings = ref(false)
const settingsLoading = ref(false)
const settingsSaving = ref(false)
const settingsError = ref('')
const settingsMessage = ref('')
const wechatTesting = ref(false)
const profileSaving = ref(false)
const profileMotto = ref('')
const passwordForm = ref({ currentPassword: '', newPassword: '' })
const passwordSaving = ref(false)
const notificationSettings = ref({
  due24hEnabled: true,
  wechatEnabled: false,
  wechatOpenid: '',
  wechatBound: false,
  wechatMode: 'log',
  wechatConfigured: true,
  wechatBindingAvailable: false,
})
const student = ref({ name: '林瑞轩', school: '', term: '' })
const teacher = ref({ name: '', school: '', applicationStatus: '' })
const teacherView = ref('概览')
const teacherTerms = ref([])
const teacherCourses = ref([])
const teacherClasses = ref([])
const teacherDeadlines = ref([])
const teacherForm = ref({ name: '', email: '', password: '', schoolId: '', proof: '' })
const newClass = ref({ courseId: '', courseName: '', termId: '', name: '', startDate: '', endDate: '' })
const newDeadline = ref({ classId: '', title: '', dueAt: '', kind: 'formative', description: '' })
const editingDeadline = ref(null)
const teacherError = ref('')
const teacherMessage = ref('')
const subscriptionError = ref('')

function csrfToken() {
  return document.cookie
    .split('; ')
    .find((item) => item.startsWith('csrftoken='))
    ?.split('=')[1] || ''
}

function apiFetch(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = new Headers(options.headers || {})
  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    headers.set('X-CSRFToken', decodeURIComponent(csrfToken()))
  }
  return window.fetch(url, { credentials: 'same-origin', ...options, headers })
}

function uploadChatMessage(url, formData, progress = chatUploadProgress) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('POST', url)
    request.withCredentials = true
    const token = decodeURIComponent(csrfToken())
    if (token) request.setRequestHeader('X-CSRFToken', token)
    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) return
      progress.value = Math.max(1, Math.round((event.loaded / event.total) * 100))
    }
    request.onerror = () => reject(new Error('网络中断，文件尚未发送。'))
    request.onabort = () => reject(new Error('文件上传已取消。'))
    request.onload = () => {
      let data = {}
      try {
        data = JSON.parse(request.responseText || '{}')
      } catch {
        reject(new Error('服务器返回了无效响应。'))
        return
      }
      if (request.status < 200 || request.status >= 300) {
        reject(new Error(data.error || '发送消息失败'))
        return
      }
      resolve(data)
    }
    request.send(formData)
  })
}

const today = ref('2026-08-31')
const todayTasks = computed(() => tasks.value.filter((task) => task.date === selectedDate.value).sort((a, b) => a.time.localeCompare(b.time)))
const dashboardTodayTasks = computed(() => tasks.value
  .filter((task) => task.date === today.value)
  .sort((a, b) => a.time.localeCompare(b.time)))
const dashboardTimelineTasks = computed(() => {
  const sortedTasks = tasks.value
    .filter((task) => (
      task.plannedStart?.date === today.value
      || (task.kind !== 'personal' && !task.plannedStart && task.date === today.value)
    ))
    .slice()
    .sort((a, b) => {
      const startDiff = timelineStartMinutes(a) - timelineStartMinutes(b)
      if (startDiff) return startDiff
      const durationDiff = timelineTaskDuration(b) - timelineTaskDuration(a)
      if (durationDiff) return durationDiff
      return String(a.id).localeCompare(String(b.id))
    })
  const lanes = []
  let groupId = -1
  let groupEnd = -1
  const positionedTasks = sortedTasks.map((task) => {
    const start = timelineStartMinutes(task)
    const isResizing = resizeDraft.value?.id === task.id
    const isDuration = Boolean(isResizing || hasTimelineDuration(task))
    const end = isResizing ? resizeDraft.value.end : timelineEndMinutes(task)
    const collisionStart = isDuration
      ? start
      : Math.max(0, start - timelinePointVisualPadding)
    const layoutEnd = isDuration
      ? Math.max(end, start + timelineMinimumVisualDuration)
      : Math.min(1440, start + timelinePointVisualPadding)
    if (collisionStart >= groupEnd) {
      groupId += 1
      groupEnd = layoutEnd
      lanes.length = 0
    } else {
      groupEnd = Math.max(groupEnd, layoutEnd)
    }
    let lane = lanes.findIndex((lastEnd) => collisionStart >= lastEnd)
    if (lane === -1) lane = lanes.length
    lanes[lane] = layoutEnd
    return {
      ...task,
      groupId,
      lane,
      layoutEnd,
      collisionStart,
      timelineStart: start,
      timelineEnd: end,
    }
  })
  const laneCounts = positionedTasks.reduce((counts, task) => {
    counts[task.groupId] = Math.max(counts[task.groupId] || 0, task.lane + 1)
    return counts
  }, {})
  return positionedTasks.map((task) => ({
    ...task,
    laneCount: laneCounts[task.groupId] || 1,
  }))
})
const dashboardTimelineLaneCount = computed(() => Math.max(
  1,
  dashboardTimelineTasks.value.reduce((max, task) => Math.max(max, task.lane), 0) + 1,
))
const timelineOverviewHeight = computed(() => Math.min(
  112,
  Math.max(54, 26 + dashboardTimelineLaneCount.value * 12),
))
const dashboardOfficialTodayTasks = computed(() => dashboardTodayTasks.value.filter((task) => task.kind !== 'personal'))
const dashboardPersonalTodayTasks = computed(() => dashboardTodayTasks.value.filter((task) => task.kind === 'personal'))
const dashboardUnscheduledPersonalTasks = computed(() => dashboardPersonalTodayTasks.value.filter((task) => !task.plannedStart))
const dashboardCompletedCount = computed(() => dashboardTodayTasks.value.filter((task) => task.done).length)
const dashboardCompletionPercent = computed(() => dashboardTodayTasks.value.length
  ? Math.round((dashboardCompletedCount.value / dashboardTodayTasks.value.length) * 100)
  : 0)
const dashboardRemainingCount = computed(() => Math.max(
  0,
  dashboardTodayTasks.value.length - dashboardCompletedCount.value,
))
const dashboardTodayState = computed(() => {
  if (!dashboardTodayTasks.value.length) return 'empty'
  if (dashboardCompletionPercent.value === 100) return 'complete'
  if (dashboardTodayTasks.value.some((task) => task.level === 'urgent' && !task.done)) return 'urgent'
  return 'steady'
})
const dashboardStateCopy = computed(() => ({
  empty: {
    label: '留白日',
    title: '今天给自己留一点空间',
    description: '没有必须完成的任务，去安排一件真正想做的事。',
  },
  urgent: {
    label: '需要聚焦',
    title: `还有 ${dashboardRemainingCount.value} 项值得优先处理`,
    description: '先处理距离截止较近的安排，完成一项就轻松一点。',
  },
  complete: {
    label: '今日完成',
    title: '今天的安排已经收好',
    description: '任务全部完成，今天的打卡也已经记录。',
  },
  steady: {
    label: '稳步推进',
    title: `今天完成了 ${dashboardCompletedCount.value} 项`,
    description: '按自己的节奏推进，下一项也可以从容开始。',
  },
}[dashboardTodayState.value]))
const dashboardTaskBreakdown = computed(() => [
  { label: '官方 DDL', value: dashboardOfficialTodayTasks.value.length, tone: 'official' },
  { label: '个人 ToDo', value: dashboardPersonalTodayTasks.value.length, tone: 'personal' },
  { label: '已完成', value: dashboardCompletedCount.value, tone: 'done' },
  { label: '待完成', value: dashboardRemainingCount.value, tone: 'remaining' },
])
const dashboardRecentCheckins = computed(() => {
  const recent = dashboard.value.checkin?.recent || []
  if (recent.length) return recent
  return Array.from({ length: 7 }, (_, offset) => ({
    date: toIsoDate(addDays(today.value, offset - 6)),
    checkedIn: false,
    percent: 0,
  }))
})
const dashboardWeekdayLabel = (iso) => {
  const date = dateFromIso(iso)
  return ['日', '一', '二', '三', '四', '五', '六'][date.getDay()]
}
const dashboardCheckinLabel = (item) => (
  item.date === today.value ? '今天' : `周${dashboardWeekdayLabel(item.date)}`
)
function scrollToDashboardToday() {
  dashboardProgressExpanded.value = false
  nextTick(() => {
    dashboardTodayGridRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}
const personalSavedPosts = computed(() => communityPosts.value.filter((post) => post.saved))
const personalMyPosts = computed(() => communityPosts.value.filter((post) => post.author === student.value.name))
const personalJoinedGroups = computed(() => communityGroups.value.filter((group) => group.joined))
const personalJoinedEvents = computed(() => communityEvents.value.filter((event) => event.joined))
const personalActivityCount = computed(() => personalMyPosts.value.length + personalSavedPosts.value.length + personalJoinedGroups.value.length)
const friendList = computed(() => friendUsers.value.filter((user) => user.status === 'friend'))
const incomingFriendRequests = computed(() => friendUsers.value.filter((user) => user.status === 'pending_received'))
const outgoingFriendRequests = computed(() => friendUsers.value.filter((user) => user.status === 'pending_sent'))
const friendRequestCount = computed(() => incomingFriendRequests.value.length)
const filteredFriendUsers = computed(() => {
  const keyword = friendQuery.value.trim().toLowerCase()
  const list = friendTab.value === '我的好友'
    ? friendList.value
    : friendTab.value === '好友申请'
      ? [...incomingFriendRequests.value, ...outgoingFriendRequests.value]
      : friendUsers.value.filter((user) => user.status !== 'friend')
  if (!keyword) return list
  return list.filter((user) => `${user.name} ${user.school} ${user.grade} ${user.bio}`.toLowerCase().includes(keyword))
})
const friendStats = computed(() => [
  { label: '我的好友', value: friendList.value.length, tone: 'blue' },
  { label: '待处理申请', value: friendRequestCount.value, tone: 'orange' },
  { label: '共同好友', value: friendUsers.value.reduce((sum, user) => sum + (user.mutual || 0), 0), tone: 'green' },
])
const unreadChatCount = computed(() => chats.value.reduce((sum, chat) => sum + (chat.unread || 0), 0))
const filteredChats = computed(() => {
  const keyword = chatQuery.value.trim().toLowerCase()
  if (!keyword) return chats.value
  return chats.value.filter((chat) => `${chat.name} ${chat.school} ${chat.grade} ${chat.lastMessage}`.toLowerCase().includes(keyword))
})
const filteredChatGroups = computed(() => {
  const keyword = chatQuery.value.trim().toLowerCase()
  if (!keyword) return chatGroups.value
  return chatGroups.value.filter((group) => (
    `${group.name} ${group.kindLabel} ${group.description}`.toLowerCase().includes(keyword)
  ))
})
const chatGroupInvitationCount = computed(() => chatGroupInvitations.value.length)
const filteredChatMessages = computed(() => {
  const keyword = chatMessageQuery.value.trim().toLowerCase()
  return chatMessages.value.filter((message) => {
    if (chatHiddenMessageIds.value.includes(message.id)) return false
    if (!keyword) return true
    return `${message.content || ''} ${message.imageUrl ? '图片' : ''} ${message.time || ''}`
      .toLowerCase()
      .includes(keyword)
  })
})
const shareableChatTasks = computed(() => tasks.value
  .filter((task) => !task.done)
  .slice()
  .sort((a, b) => `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`))
  .slice(0, 8))
function normalizeChat(chat) {
  return { ...chat, userId: chat.userId ?? chat.id }
}
function formatFileSize(size) {
  if (!size) return '未知大小'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}
function isAudioAttachment(attachment) {
  return Boolean(
    attachment
    && (
      attachment.type?.startsWith('audio/')
      || /\.(mp3|wav|m4a|webm|ogg)$/i.test(attachment.name || '')
    ),
  )
}
function scrollChatToBottom() {
  nextTick(() => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    }
  })
}
function scrollChatGroupToBottom() {
  nextTick(() => {
    if (chatGroupMessagesRef.value) {
      chatGroupMessagesRef.value.scrollTop = chatGroupMessagesRef.value.scrollHeight
    }
  })
}
function openChatImage(imageUrl) {
  if (imageUrl) chatImageViewer.value = imageUrl
}
function closeChatImage() {
  chatImageViewer.value = ''
}
const personalSpaceStats = computed(() => ([
  { label: '本周完成', value: `${dashboardCompletionPercent.value}%`, tone: 'blue' },
  { label: '连续打卡', value: `${dashboard.value.checkin.streak || 0} 天`, tone: 'green' },
  { label: '收藏内容', value: `${personalSavedPosts.value.length} 条`, tone: 'orange' },
  { label: '参与圈子', value: `${personalJoinedGroups.value.length} 个`, tone: 'purple' },
]))
const personalBadges = computed(() => ([
  { title: '计划执行者', desc: '完成本周的学习安排', active: dashboardCompletionPercent.value >= 60 },
  { title: '社区参与者', desc: '发布或评论过内容', active: personalActivityCount.value >= 1 },
  { title: '协作成员', desc: '加入学习小组或活动', active: personalJoinedGroups.value.length >= 1 },
  { title: '成长记录', desc: '保存过值得复用的经验', active: personalSavedPosts.value.length >= 1 },
]))
const dashboardWeekTasks = computed(() => {
  const ids = new Set((dashboard.value.week.tasks || []).map((task) => task.id))
  return tasks.value
    .filter((task) => ids.has(task.id))
    .sort((a, b) => `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`))
})
const dashboardFocusWeekTask = computed(() => dashboardWeekTasks.value.find((task) => !task.done && task.level !== 'expired') || dashboardWeekTasks.value[0] || null)
const dashboardVisibleWeekTasks = computed(() => showAllWeekTasks.value
  ? dashboardWeekTasks.value
  : dashboardWeekTasks.value.slice(0, 5))
const dashboardHiddenWeekCount = computed(() => Math.max(0, dashboardWeekTasks.value.length - 5))
const annualRange = computed(() => {
  const start = new Date(annualPlanYear.value, annualPlanStartMonth.value, 1)
  const end = new Date(annualPlanYear.value, annualPlanStartMonth.value + annualPlanZoom.value, 1)
  return { start, end }
})
const annualVisibleMonths = computed(() => Array.from(
  { length: annualPlanZoom.value },
  (_, index) => new Date(annualPlanYear.value, annualPlanStartMonth.value + index, 1),
))
const annualRangeLabel = computed(() => {
  const start = annualVisibleMonths.value[0]
  const end = annualVisibleMonths.value.at(-1)
  return start && end ? `${start.getMonth() + 1}月 - ${end.getMonth() + 1}月` : ''
})
const annualTodayPosition = computed(() => {
  if (Number(today.value.slice(0, 4)) !== annualPlanYear.value) return null
  const current = dateFromIso(today.value)
  const { start, end } = annualRange.value
  if (current < start || current >= end) return null
  const position = ((current.getTime() - start.getTime()) / (end.getTime() - start.getTime())) * 100
  return 8 + position * 0.92
})
const annualVisibleTasks = computed(() => annualPlanTasks.value.filter((task) => (
  visibleAnnualCategories.value.includes(task.category)
  && annualTaskInRange(task)
)))
const annualPlanSummary = computed(() => ({
  total: annualPlanTasks.value.length,
  inProgress: annualPlanTasks.value.filter((task) => task.status === 'in_progress').length,
  completed: annualPlanTasks.value.filter((task) => task.status === 'completed').length,
}))
const timelineTasks = computed(() => {
  const lanes = []
  return todayTasks.value.map((task) => {
    const position = timePosition(task.time)
    let lane = lanes.findIndex((lastPosition) => position - lastPosition >= 12)
    if (lane === -1) lane = lanes.length
    lanes[lane] = position
    return { ...task, lane }
  })
})
const timelineHeight = computed(() => Math.max(214, 142 + timelineTasks.value.reduce((max, task) => Math.max(max, task.lane), 0) * 88))
const activeTasks = computed(() => tasks.value.filter((task) => !task.done && task.level !== 'expired'))
const unreadNotificationCount = computed(() => notifications.value.filter((notification) => !notification.read).length)
const globalSearchTaskResults = computed(() => {
  const keyword = globalQuery.value.trim().toLowerCase()
  if (!keyword) return []
  return tasks.value
    .filter((task) => `${task.title} ${task.sourceName} ${task.publisher}`.toLowerCase().includes(keyword))
    .slice()
    .sort((a, b) => `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`))
    .slice(0, 8)
})
const globalSearchSubscriptionResults = computed(() => {
  const keyword = globalQuery.value.trim().toLowerCase()
  if (!keyword) return []
  return subscriptions.value
    .filter((item) => `${item.name} ${item.publisher}`.toLowerCase().includes(keyword))
    .slice(0, 5)
})
const weekTasks = computed(() => {
  const weekEnd = toIsoDate(addDays(today.value, 6))
  return activeTasks.value.filter((task) => task.date >= today.value && task.date <= weekEnd)
})
const todayLabel = computed(() => {
  const date = new Date(`${today.value}T12:00:00`)
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日，星期${weekdays[date.getDay()]}`
})
const calendarMonthLabel = computed(() => {
  const date = dateFromIso(selectedDate.value)
  return `${date.getFullYear()}年${date.getMonth() + 1}月`
})
const filteredSubscriptions = computed(() => subscriptions.value.filter((item) => {
  const tabMatch = filter.value === '全部'
    || (filter.value === '我的课程' && item.subscribed)
    || (filter.value === '升学' && item.type === '升学')
  return tabMatch && `${item.name}${item.publisher}`.toLowerCase().includes(query.value.toLowerCase())
}))
const miniMonthDays = computed(() => buildMonthDays(selectedDate.value))
const calendarMonthDays = computed(() => buildMonthDays(calendarCursor.value))
const calendarWeekDays = computed(() => {
  const weekStart = startOfWeek(calendarCursor.value)
  return Array.from({ length: 7 }, (_, index) => {
    const date = addDays(weekStart, index)
    const iso = toIsoDate(date)
    return {
      iso,
      number: date.getDate(),
      weekday: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][index],
      isToday: iso === today.value,
      tasks: tasks.value.filter((task) => task.date === iso).sort((a, b) => a.time.localeCompare(b.time)),
    }
  })
})
const calendarSelectedTasks = computed(() => tasks.value
  .filter((task) => task.date === selectedDate.value)
  .sort((a, b) => a.time.localeCompare(b.time)))
const dayHours = computed(() => Array.from({ length: 24 }, (_, hour) => String(hour).padStart(2, '0')))
const calendarPeriodLabel = computed(() => {
  const cursor = dateFromIso(calendarCursor.value)
  if (calendarMode.value === '月') return `${cursor.getFullYear()}年${cursor.getMonth() + 1}月`
  if (calendarMode.value === '周') {
    const start = startOfWeek(calendarCursor.value)
    const end = addDays(start, 6)
    return `${start.getMonth() + 1}月${start.getDate()}日 - ${end.getMonth() + 1}月${end.getDate()}日`
  }
  return `${cursor.getMonth() + 1}月${cursor.getDate()}日`
})

function buildMonthDays(anchor) {
  const selected = dateFromIso(anchor)
  const first = new Date(selected.getFullYear(), selected.getMonth(), 1)
  const offset = (first.getDay() + 6) % 7
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(selected.getFullYear(), selected.getMonth(), index - offset + 1)
    const iso = toIsoDate(date)
    return {
      number: date.getDate(),
      iso,
      outside: date.getMonth() !== selected.getMonth(),
      tasks: tasks.value.filter((task) => task.date === iso),
    }
  })
}
const remainingTime = computed(() => selectedTask.value ? (selectedTask.value.date === today.value ? `今天 ${selectedTask.value.time}` : `${selectedTask.value.date} ${selectedTask.value.time}`) : '')
const selectedSchool = computed(() => schoolOptions.value.find((school) => String(school.id) === String(authForm.value.schoolId)))
const selectedTerms = computed(() => selectedSchool.value?.terms || [])

async function updateDeadlineState(task, payload, { refresh = true } = {}) {
  const endpoint = task.deadlineId
    ? `/api/deadlines/${task.deadlineId}/state/`
    : `/api/personal-tasks/${task.personalTaskId}/state/`
  const response = await apiFetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || '保存任务状态失败')
  Object.assign(task, data)
  if (refresh) await loadDashboard()
  return data
}
async function toggleTask(task) {
  try {
    await updateDeadlineState(task, { done: !task.done })
  } catch (error) {
    console.error(error)
  }
}
function timePosition(time) {
  const [hour, minute] = time.split(':').map(Number)
  return ((hour * 60 + minute) / 1440) * 100
}
function timeToMinutes(time) {
  const [hour, minute] = String(time || '').split(':').map(Number)
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) return null
  if (hour === 24 && minute === 0) return 1440
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null
  return (hour * 60) + minute
}
function minutesToTime(minutes) {
  const safeMinutes = Math.max(0, Math.min(1440, Number(minutes) || 0))
  if (safeMinutes === 1440) return '24:00'
  return `${String(Math.floor(safeMinutes / 60)).padStart(2, '0')}:${String(safeMinutes % 60).padStart(2, '0')}`
}
function timelineStartMinutes(task) {
  if (timelineDragDraft.value?.id === task?.id) {
    return timelineDragDraft.value.start
  }
  const parsed = timeToMinutes(task.plannedStart?.time || task.time)
  return parsed === null ? 0 : Math.max(0, Math.min(1439, parsed))
}
function timelineEndMinutes(task) {
  const start = timelineStartMinutes(task)
  if (timelineDragDraft.value?.id === task?.id) {
    return timelineDragDraft.value.end === null
      ? Math.min(1440, start + 15)
      : timelineDragDraft.value.end
  }
  const parsed = task.plannedEnd ? timeToMinutes(task.plannedEnd.time) : null
  return parsed !== null && parsed > start
    ? Math.min(1440, parsed)
    : Math.min(1440, start + 15)
}
function hasTimelineDuration(task) {
  if (timelineDragDraft.value?.id === task?.id) {
    return timelineDragDraft.value.end !== null
  }
  if (!task?.plannedStart || !task?.plannedEnd) return false
  if (task.plannedStart.date && task.plannedEnd.date && task.plannedStart.date !== task.plannedEnd.date) return false
  const start = timelineStartMinutes(task)
  const end = timeToMinutes(task.plannedEnd.time)
  return end !== null && end > start
}
function timelineIsDuration(task) {
  return Boolean(resizeDraft.value?.id === task?.id || hasTimelineDuration(task))
}
function timelineTaskDuration(task) {
  const end = resizeDraft.value?.id === task.id ? resizeDraft.value.end : timelineEndMinutes(task)
  return Math.max(15, end - timelineStartMinutes(task))
}
function timelineTaskEndMinutes(task) {
  return resizeDraft.value?.id === task.id
    ? resizeDraft.value.end
    : timelineEndMinutes(task)
}
function timelineTaskTimeLabel(task) {
  const start = timelineStartMinutes(task)
  return timelineIsDuration(task)
    ? `${minutesToTime(start)} - ${minutesToTime(timelineTaskEndMinutes(task))}`
    : `${minutesToTime(start)} · 时间节点`
}
function timelineTaskStyle(task) {
  const start = timelineStartMinutes(task)
  const duration = timelineTaskDuration(task)
  const isDuration = timelineIsDuration(task)
  const isPoint = !isDuration
  const laneCount = task.laneCount || dashboardTimelineLaneCount.value
  const laneWidth = 100 / laneCount
  return {
    top: `${timelineHeaderHeight + (start / 60) * timelineHourHeight - (isPoint ? 14 : 0)}px`,
    height: isDuration ? `${Math.max(60, (duration / 60) * timelineHourHeight)}px` : '28px',
    left: `calc(${task.lane * laneWidth}% + 4px)`,
    width: `calc(${laneWidth}% - 8px)`,
    '--timeline-task-width': `calc(${laneWidth}% - 8px)`,
    '--timeline-lane-count': laneCount,
  }
}
const timelineDragLabel = computed(() => {
  if (timelineDragMinutes.value === null) return ''
  const task = draggingTask.value
  if (!task) return ''
  const duration = hasTimelineDuration(task)
    ? Math.max(15, timelineEndMinutes(task) - timelineStartMinutes(task))
    : null
  return duration ? `${minutesToTime(timelineDragMinutes.value)} · ${duration} 分钟` : `${minutesToTime(timelineDragMinutes.value)} · 时间节点`
})
const timelineNowPosition = computed(() => {
  const current = shanghaiClockParts(nowTick.value)
  const todayDate = dateFromIso(today.value)
  if (
    current.year !== todayDate.getFullYear()
    || current.month !== todayDate.getMonth() + 1
    || current.day !== todayDate.getDate()
  ) return null
  return timelineHeaderHeight + ((current.hour * 60 + current.minute) / 60) * timelineHourHeight
})
const timelineNowMinutes = computed(() => {
  if (timelineNowPosition.value === null) return 12 * 60
  const current = shanghaiClockParts(nowTick.value)
  return current.hour * 60 + current.minute
})
function countdownLabel(task) {
  if (!task?.iso) return '待安排'
  const remaining = new Date(task.iso).getTime() - nowTick.value
  if (remaining <= 0) return '已过期'
  const totalHours = Math.floor(remaining / 3600000)
  const days = Math.floor(totalHours / 24)
  const hours = totalHours % 24
  if (days) return `${days}天${hours}小时`
  return `${Math.max(1, hours)}小时内`
}
function shanghaiClockParts(epoch = Date.now()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(epoch))
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return {
    year: Number(values.year),
    month: Number(values.month),
    day: Number(values.day),
    hour: Number(values.hour),
    minute: Number(values.minute),
  }
}
function dateFromIso(value) {
  return new Date(`${value}T12:00:00`)
}
function toIsoDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
function addDays(value, amount) {
  const date = typeof value === 'string' ? dateFromIso(value) : new Date(value)
  date.setDate(date.getDate() + amount)
  return date
}
function annualCategory(categoryId) {
  return annualCategories.find((category) => category.id === categoryId) || annualCategories[0]
}
function annualTaskInRange(task) {
  const { start, end } = annualRange.value
  if (task.type === 'node') {
    const node = dateFromIso(task.nodeDate)
    return node >= start && node < end
  }
  return dateFromIso(task.startDate) < end && dateFromIso(task.endDate) >= start
}
function annualTaskStyle(task) {
  const { start, end } = annualRange.value
  const category = annualCategory(task.category)
  const total = end.getTime() - start.getTime()
  if (task.type === 'node') {
    const node = dateFromIso(task.nodeDate)
    return {
      left: `${Math.max(0, Math.min(100, ((node.getTime() - start.getTime()) / total) * 100))}%`,
      '--category-color': category.color,
    }
  }
  const taskStart = dateFromIso(task.startDate)
  const taskEnd = addDays(task.endDate, 1)
  const visibleStart = taskStart < start ? start : taskStart
  const visibleEnd = taskEnd > end ? end : taskEnd
  const left = ((visibleStart.getTime() - start.getTime()) / total) * 100
  const width = ((visibleEnd.getTime() - visibleStart.getTime()) / total) * 100
  const localToday = dateFromIso(today.value)
  const progress = Math.max(0, Math.min(1, (
    localToday.getTime() - visibleStart.getTime()
  ) / Math.max(1, visibleEnd.getTime() - visibleStart.getTime())))
  return {
    left: `${left}%`,
    width: `${Math.max(width, 1.2)}%`,
    '--category-color': category.color,
    '--task-progress': `${progress * 100}%`,
  }
}
function toggleAnnualCategory(categoryId) {
  visibleAnnualCategories.value = visibleAnnualCategories.value.includes(categoryId)
    ? visibleAnnualCategories.value.filter((id) => id !== categoryId)
    : [...visibleAnnualCategories.value, categoryId]
}
function setAnnualZoom(months) {
  annualPlanZoom.value = months
  const currentMonth = Number(today.value.slice(5, 7)) - 1
  const maxStart = 12 - months
  annualPlanStartMonth.value = months === 12
    ? 0
    : Math.max(0, Math.min(maxStart, currentMonth - Math.floor(months / 2)))
}
function shiftAnnualRange(direction) {
  const maxStart = 12 - annualPlanZoom.value
  annualPlanStartMonth.value = Math.max(
    0,
    Math.min(maxStart, annualPlanStartMonth.value + direction * Math.max(1, Math.floor(annualPlanZoom.value / 2))),
  )
}
function goToAnnualToday() {
  annualPlanYear.value = Number(today.value.slice(0, 4))
  setAnnualZoom(annualPlanZoom.value)
}
function resetAnnualPlanForm() {
  editingAnnualPlanTask.value = null
  annualPlanForm.value = {
    category: 'application',
    type: 'period',
    title: '',
    startDate: today.value,
    endDate: today.value,
    nodeDate: today.value,
    description: '',
  }
}
function openAnnualPlanEditor(task = null) {
  if (!task) {
    resetAnnualPlanForm()
  } else {
    editingAnnualPlanTask.value = { ...task }
    annualPlanForm.value = {
      category: task.category,
      type: task.type,
      title: task.title,
      startDate: task.startDate || '',
      endDate: task.endDate || '',
      nodeDate: task.nodeDate || '',
      description: task.description || '',
    }
  }
  annualPlanError.value = ''
  annualPlanDeletePending.value = null
  annualPlanEditorOpen.value = true
}
function replaceAnnualPlanTask(updated) {
  const index = annualPlanTasks.value.findIndex((task) => task.id === updated.id)
  if (index >= 0) annualPlanTasks.value[index] = updated
  else annualPlanTasks.value.push(updated)
  if (annualPlanDetail.value?.id === updated.id) annualPlanDetail.value = updated
}
async function loadAnnualPlan() {
  annualPlanLoading.value = true
  annualPlanError.value = ''
  try {
    const response = await apiFetch(`/api/annual-plan/?year=${annualPlanYear.value}`)
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '加载年度规划失败')
    annualPlanTasks.value = data.tasks
  } catch (error) {
    annualPlanError.value = error.message
  } finally {
    annualPlanLoading.value = false
  }
}
async function saveAnnualPlanTask() {
  const editing = editingAnnualPlanTask.value
  if (
    annualPlanForm.value.type === 'period'
    && annualPlanForm.value.startDate
    && annualPlanForm.value.endDate
    && annualPlanForm.value.endDate < annualPlanForm.value.startDate
  ) {
    annualPlanError.value = '结束日期不能早于开始日期。'
    return
  }
  annualPlanSaving.value = true
  annualPlanError.value = ''
  try {
    const response = await apiFetch(
      editing ? `/api/annual-plan/${editing.id}/` : '/api/annual-plan/',
      {
        method: editing ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...annualPlanForm.value }),
      },
    )
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '保存年度任务失败')
    replaceAnnualPlanTask(data)
    annualPlanEditorOpen.value = false
    annualPlanDeletePending.value = null
  } catch (error) {
    annualPlanError.value = error.message || '保存年度任务失败'
  } finally {
    annualPlanSaving.value = false
  }
}
function requestDeleteAnnualPlanTask(task) {
  annualPlanError.value = ''
  annualPlanDeletePending.value = task
}
function cancelDeleteAnnualPlanTask() {
  annualPlanDeletePending.value = null
}
async function deleteAnnualPlanTask(task) {
  if (!task || annualPlanDeleting.value) return
  annualPlanDeleting.value = true
  annualPlanError.value = ''
  try {
    const response = await apiFetch(`/api/annual-plan/${task.id}/`, { method: 'DELETE' })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.error || '删除年度任务失败')
    annualPlanTasks.value = annualPlanTasks.value.filter((item) => item.id !== task.id)
    annualPlanDetail.value = null
    annualPlanEditorOpen.value = false
    annualPlanDeletePending.value = null
  } catch (error) {
    annualPlanError.value = error.message || '删除年度任务失败'
  } finally {
    annualPlanDeleting.value = false
  }
}
async function addAnnualPlanSubtask() {
  if (!annualPlanDetail.value || !annualPlanSubtaskDraft.value.title.trim()) return
  const response = await apiFetch(`/api/annual-plan/${annualPlanDetail.value.id}/subtasks/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(annualPlanSubtaskDraft.value),
  })
  const data = await response.json()
  if (!response.ok) {
    annualPlanError.value = data.error || '添加子任务失败'
    return
  }
  replaceAnnualPlanTask(data)
  annualPlanSubtaskDraft.value = { title: '', dueDate: '' }
}
function editAnnualPlanSubtask(subtask) {
  editingAnnualPlanSubtaskId.value = subtask.id
  annualPlanSubtaskEdit.value = { title: subtask.title, dueDate: subtask.dueDate || '' }
}
async function saveAnnualPlanSubtask(subtask, payload = null) {
  if (!annualPlanDetail.value) return
  const response = await apiFetch(
    `/api/annual-plan/${annualPlanDetail.value.id}/subtasks/${subtask.id}/`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || annualPlanSubtaskEdit.value),
    },
  )
  const data = await response.json()
  if (!response.ok) {
    annualPlanError.value = data.error || '保存子任务失败'
    return
  }
  replaceAnnualPlanTask(data)
  editingAnnualPlanSubtaskId.value = null
}
async function deleteAnnualPlanSubtask(subtask) {
  if (!annualPlanDetail.value || !window.confirm(`删除子任务“${subtask.title}”？`)) return
  const response = await apiFetch(
    `/api/annual-plan/${annualPlanDetail.value.id}/subtasks/${subtask.id}/`,
    { method: 'DELETE' },
  )
  if (!response.ok) {
    annualPlanError.value = '删除子任务失败'
    return
  }
  replaceAnnualPlanTask(await response.json())
}
function startOfWeek(value) {
  const date = dateFromIso(value)
  const offset = (date.getDay() + 6) % 7
  return addDays(date, -offset)
}
function selectCalendarDate(iso, task = null) {
  selectedDate.value = iso
  calendarCursor.value = iso
  selectedTask.value = task
}
function setCalendarMode(mode) {
  calendarMode.value = mode
  calendarCursor.value = selectedDate.value
}
function openDayView(iso) {
  selectCalendarDate(iso)
  calendarMode.value = '日'
}
function shiftCalendar(direction) {
  const cursor = dateFromIso(calendarCursor.value)
  if (calendarMode.value === '月') cursor.setMonth(cursor.getMonth() + direction)
  if (calendarMode.value === '周') cursor.setDate(cursor.getDate() + direction * 7)
  if (calendarMode.value === '日') cursor.setDate(cursor.getDate() + direction)
  calendarCursor.value = toIsoDate(cursor)
  selectedDate.value = calendarCursor.value
  selectedTask.value = null
}
function goToToday() {
  calendarCursor.value = today.value
  selectedDate.value = today.value
  selectedTask.value = null
}
function shiftMiniMonth(direction) {
  const cursor = dateFromIso(selectedDate.value)
  cursor.setMonth(cursor.getMonth() + direction)
  selectedDate.value = toIsoDate(cursor)
  calendarCursor.value = selectedDate.value
  selectedTask.value = null
}
function tasksAtHour(hour) {
  return calendarSelectedTasks.value.filter((task) => task.time.slice(0, 2) === hour)
}
function startDrag(task, event = null) {
  draggingTask.value = task
  timelineError.value = ''
  if (event?.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', task.id)
  }
}
function timelineMinutesFromEvent(event, task = draggingTask.value) {
  return timelineMinutesFromClientY(event.clientY, task)
}
function timelineRawMinutesFromClientY(clientY) {
  if (!timelineBoardRef.value) return null
  const rect = adjustedPointerRect(pointerDropGeometries?.timeline)
    || timelineBoardRef.value.getBoundingClientRect()
  return ((clientY - rect.top + timelineBoardRef.value.scrollTop - timelineHeaderHeight) / timelineHourHeight) * 60
}
function timelineMinutesFromClientY(clientY, task = draggingTask.value, grabOffsetMinutes = 0) {
  const rawMinutes = timelineRawMinutesFromClientY(clientY)
  if (rawMinutes === null) return null
  const duration = hasTimelineDuration(task)
    ? Math.max(15, timelineEndMinutes(task) - timelineStartMinutes(task))
    : null
  const latestStart = duration ? Math.max(0, 1440 - duration) : 1425
  return Math.max(0, Math.min(
    latestStart,
    Math.round((rawMinutes - grabOffsetMinutes) / 15) * 15,
  ))
}
function scrollTimelineToMinutes(minutes = 12 * 60) {
  if (!timelineBoardRef.value) return
  const target = timelineHeaderHeight + (Math.max(0, Math.min(1440, minutes)) / 60) * timelineHourHeight
  timelineBoardRef.value.scrollTo({
    top: Math.max(0, target - 180),
    behavior: 'smooth',
  })
}
function scrollTimelineFromOverview(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))
  scrollTimelineToMinutes(Math.round((ratio * 1440) / 15) * 15)
}
function pointInRect(clientX, clientY, rect) {
  return Boolean(
    rect
    && clientX >= rect.left
    && clientX <= rect.right
    && clientY >= rect.top
    && clientY <= rect.bottom,
  )
}
function pointerDropZone(clientX, clientY) {
  const geometries = pointerDropGeometries || {
    todo: todoPanelRef.value?.getBoundingClientRect(),
    timeline: timelineBoardRef.value?.getBoundingClientRect(),
    urgent: urgentDropZoneRef.value?.getBoundingClientRect(),
    completed: completedDropZoneRef.value?.getBoundingClientRect(),
  }
  if (pointInRect(clientX, clientY, adjustedPointerRect(geometries.todo))) return 'todo'
  if (pointInRect(clientX, clientY, adjustedPointerRect(geometries.timeline))) return 'timeline'
  if (pointInRect(clientX, clientY, adjustedPointerRect(geometries.urgent))) return 'urgent'
  if (pointInRect(clientX, clientY, adjustedPointerRect(geometries.completed))) return 'completed'
  return ''
}
function pageScrollTop() {
  return (document.scrollingElement || document.documentElement).scrollTop
}
function adjustedPointerRect(entry) {
  if (!entry) return null
  const rect = entry.rect || entry
  if (!rect) return null
  if (entry.capturedScrollTop === undefined) return rect
  const delta = entry.capturedScrollTop - pageScrollTop()
  return {
    left: rect.left,
    right: rect.right,
    top: rect.top + delta,
    bottom: rect.bottom + delta,
  }
}
function cachePointerDropGeometries() {
  const capturedScrollTop = pageScrollTop()
  pointerDropGeometries = {
    todo: { rect: todoPanelRef.value?.getBoundingClientRect(), capturedScrollTop },
    timeline: { rect: timelineBoardRef.value?.getBoundingClientRect(), capturedScrollTop },
    urgent: { rect: urgentDropZoneRef.value?.getBoundingClientRect(), capturedScrollTop },
    completed: { rect: completedDropZoneRef.value?.getBoundingClientRect(), capturedScrollTop },
  }
}
function clearPointerDropGeometries() {
  pointerDropGeometries = null
}
function scheduleDashboardRefresh() {
  if (dashboardRefreshTimer) return
  dashboardRefreshTimer = window.setTimeout(() => {
    dashboardRefreshTimer = null
    loadDashboard().catch((error) => {
      console.error('刷新 Dashboard 失败', error)
    })
  }, 280)
}
function updatePointerDragTarget(clientX, clientY) {
  pagePointerClientX = clientX
  pagePointerClientY = clientY
  timelinePointerClientY = clientY
  const zone = pointerDropZone(clientX, clientY)
  if (dragOverZone.value !== zone) dragOverZone.value = zone
  if (zone === 'timeline') {
    if (shouldPageAutoScroll(clientY, zone)) {
      stopTimelineAutoScroll()
      startPageAutoScroll()
    } else {
      stopPageAutoScroll()
      startTimelineAutoScroll()
    }
    const nextMinutes = timelineMinutesFromClientY(
      clientY,
      draggingTask.value,
      pointerDrag.value?.grabOffsetMinutes || 0,
    )
    if (timelineElementPreview?.task.id === draggingTask.value?.id) {
      const duration = timelineElementPreview.end === null
        ? null
        : Math.max(15, timelineElementPreview.end - timelineElementPreview.start)
      applyTimelineElementPreview(
        pointerDrag.value,
        nextMinutes,
        duration === null ? null : Math.min(1440, nextMinutes + duration),
      )
      // Scheduled tasks use a direct DOM preview. Keep the reactive tree
      // completely untouched while the pointer is moving.
      if (timelineDragMinutes.value !== null) timelineDragMinutes.value = null
      if (timelineDragDraft.value !== null) timelineDragDraft.value = null
    } else {
      // A task coming from ToDo has no element on the canvas yet. Only update
      // the lightweight drop marker and the pointer session; avoid rebuilding
      // every timeline lane on each 15-minute snap.
      if (timelineDragMinutes.value !== nextMinutes) timelineDragMinutes.value = nextMinutes
      if (pointerDrag.value) {
        pointerDrag.value.previewStart = nextMinutes
        pointerDrag.value.previewEnd = null
      }
    }
  } else if (timelineDragMinutes.value !== null) {
    timelineDragMinutes.value = null
    timelineDragDraft.value = null
    if (timelineElementPreview) restoreTimelineElementPreview()
    stopTimelineAutoScroll()
    startPageAutoScroll()
  } else {
    timelineDragDraft.value = null
    if (timelineElementPreview) restoreTimelineElementPreview()
    startPageAutoScroll()
  }
}
function updateTimelineDragDraft(task, startMinutes) {
  if (!task || startMinutes === null) return
  const originalStart = timeToMinutes(task.plannedStart?.time || task.time)
  const originalEnd = task.plannedEnd ? timeToMinutes(task.plannedEnd.time) : null
  const duration = originalEnd !== null && originalEnd > originalStart
    ? originalEnd - originalStart
    : null
  const end = duration ? Math.min(1440, startMinutes + duration) : null
  const current = timelineDragDraft.value
  if (current?.id === task.id && current.start === startMinutes && current.end === end) return
  timelineDragDraft.value = { id: task.id, start: startMinutes, end }
  if (pointerDrag.value?.task.id === task.id) {
    pointerDrag.value.previewStart = startMinutes
    pointerDrag.value.previewEnd = end
  }
}
function setTimelineElementText(element, start, end, timeNodes = null, durationNode = null) {
  if (!element) return
  const label = end === null
    ? `${minutesToTime(start)} · 时间节点`
    : `${minutesToTime(start)} - ${minutesToTime(end)}`
  const nodes = timeNodes || element.querySelectorAll('.axis-task-time')
  nodes.forEach((node) => {
    node.textContent = label
  })
  const durationElement = durationNode || element.querySelector('.axis-task-duration')
  if (durationElement && end !== null) {
    durationElement.textContent = `${Math.max(15, end - start)} 分钟`
  }
}
function applyTimelineElementPreview(state, start, end) {
  const preview = timelineElementPreview
  if (!preview?.element || preview.task.id !== state.task.id) return
  state.previewStart = start
  state.previewEnd = end
  const isDuration = end !== null
  if (isDuration) {
    const offset = ((start - preview.start) / 60) * timelineHourHeight
    preview.element.style.transform = `translate3d(0, ${offset}px, 0)`
    preview.element.style.height = `${Math.max(60, ((end - start) / 60) * timelineHourHeight)}px`
  } else {
    preview.element.style.top = `${timelineHeaderHeight + (start / 60) * timelineHourHeight - 14}px`
  }
  setTimelineElementText(
    preview.element,
    start,
    end,
    preview.timeNodes,
    preview.durationNode,
  )
}
function restoreTimelineElementPreview() {
  const preview = timelineElementPreview
  if (!preview?.element) return
  preview.element.style.transform = preview.originalTransform
  preview.element.style.top = preview.originalTop
  preview.element.style.height = preview.originalHeight
  setTimelineElementText(
    preview.element,
    preview.start,
    preview.end,
    preview.timeNodes,
    preview.durationNode,
  )
  timelineElementPreview = null
}
function finishTimelineElementPreview() {
  const preview = timelineElementPreview
  if (!preview?.element) return
  preview.element.style.transform = preview.originalTransform
  timelineElementPreview = null
}
function shouldPageAutoScroll(clientY, zone = dragOverZone.value) {
  if (zone !== 'timeline' || !timelineBoardRef.value) return zone !== 'timeline'
  const boardRect = timelineBoardRef.value.getBoundingClientRect()
  const scrollingElement = document.scrollingElement || document.documentElement
  const maxScrollTop = Math.max(0, scrollingElement.scrollHeight - window.innerHeight)
  if (clientY > window.innerHeight - pageAutoScrollEdge && boardRect.bottom > window.innerHeight) {
    return scrollingElement.scrollTop < maxScrollTop
  }
  if (clientY < pageAutoScrollEdge && boardRect.top < 0) {
    return scrollingElement.scrollTop > 0
  }
  return false
}
function pageScrollDelta(clientY) {
  if (clientY < pageAutoScrollEdge) {
    return -Math.min(24, Math.max(4, Math.round((pageAutoScrollEdge - clientY) / 3)))
  }
  if (clientY > window.innerHeight - pageAutoScrollEdge) {
    return Math.min(24, Math.max(4, Math.round((clientY - (window.innerHeight - pageAutoScrollEdge)) / 3)))
  }
  return 0
}
function startPageAutoScroll() {
  if (pageAutoScrollFrame) return
  const scroll = () => {
    pageAutoScrollFrame = null
    const state = pointerDrag.value
    if (!state?.active || !shouldPageAutoScroll(pagePointerClientY, dragOverZone.value)) return
    const clientX = pagePointerClientX
    const clientY = pagePointerClientY
    if (clientX === null || clientY === null) return
    const scrollingElement = document.scrollingElement || document.documentElement
    const maxScrollTop = Math.max(0, scrollingElement.scrollHeight - window.innerHeight)
    const delta = pageScrollDelta(clientY)
    const nextScrollTop = Math.max(0, Math.min(maxScrollTop, scrollingElement.scrollTop + delta))
    if (delta && nextScrollTop !== scrollingElement.scrollTop) {
      scrollingElement.scrollTop = nextScrollTop
      updatePointerDragTarget(clientX, clientY)
    }
  }
  pageAutoScrollFrame = window.requestAnimationFrame(scroll)
}
function stopPageAutoScroll() {
  if (pageAutoScrollFrame) {
    window.cancelAnimationFrame(pageAutoScrollFrame)
    pageAutoScrollFrame = null
  }
  pagePointerClientX = null
  pagePointerClientY = null
}
function startTimelineAutoScroll() {
  if (timelineAutoScrollFrame || !timelineBoardRef.value) return
  const scroll = () => {
    timelineAutoScrollFrame = null
    const state = pointerDrag.value
    const board = timelineBoardRef.value
    if (!state?.active || dragOverZone.value !== 'timeline' || !board) return
    const clientY = timelinePointerClientY
    if (clientY === null) return
    const rect = board.getBoundingClientRect()
    const edge = 58
    let delta = 0
    if (clientY < rect.top + edge) delta = -Math.max(4, Math.round((rect.top + edge - clientY) / 8))
    if (clientY > rect.bottom - edge) delta = Math.max(4, Math.round((clientY - (rect.bottom - edge)) / 8))
    if (delta) {
      board.scrollTop = Math.max(0, Math.min(board.scrollHeight - board.clientHeight, board.scrollTop + delta))
      const nextMinutes = timelineMinutesFromClientY(
        clientY,
        draggingTask.value,
        pointerDrag.value?.grabOffsetMinutes || 0,
      )
      if (timelineDragMinutes.value !== nextMinutes) timelineDragMinutes.value = nextMinutes
      if (timelineElementPreview?.task.id === draggingTask.value?.id) {
        const duration = timelineElementPreview.end === null
          ? null
          : Math.max(15, timelineElementPreview.end - timelineElementPreview.start)
        applyTimelineElementPreview(
          pointerDrag.value,
          nextMinutes,
          duration === null ? null : Math.min(1440, nextMinutes + duration),
        )
      } else {
        if (pointerDrag.value) {
          pointerDrag.value.previewStart = nextMinutes
          pointerDrag.value.previewEnd = null
        }
      }
      timelineAutoScrollFrame = window.requestAnimationFrame(scroll)
    }
  }
  timelineAutoScrollFrame = window.requestAnimationFrame(scroll)
}
function stopTimelineAutoScroll() {
  if (!timelineAutoScrollFrame) return
  window.cancelAnimationFrame(timelineAutoScrollFrame)
  timelineAutoScrollFrame = null
  timelinePointerClientY = null
}
function beginPointerDrag(task, event) {
  if (event.button !== undefined && event.button !== 0) return
  if (event.target?.closest('button, input, textarea, select, .axis-resize-handle')) return
  if (timelineElementPreview) restoreTimelineElementPreview()
  cachePointerDropGeometries()
  const originZone = pointerDropZone(event.clientX, event.clientY)
  const pointerMinutes = originZone === 'timeline'
    ? timelineRawMinutesFromClientY(event.clientY)
    : null
  const taskStart = timelineStartMinutes(task)
  const taskEnd = hasTimelineDuration(task) ? timelineEndMinutes(task) : null
  const element = event.currentTarget?.classList?.contains('axis-task')
    ? event.currentTarget
    : null
  if (originZone === 'timeline' && element) {
    timelineElementPreview = {
      element,
      task,
      start: taskStart,
      end: taskEnd,
      timeNodes: element.querySelectorAll('.axis-task-time'),
      durationNode: element.querySelector('.axis-task-duration'),
      originalTransform: element.style.transform,
      originalTop: element.style.top,
      originalHeight: element.style.height,
    }
  }
  pointerDrag.value = {
    task,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originZone,
    grabOffsetMinutes: pointerMinutes === null || originZone !== 'timeline'
      ? 0
      : Math.max(0, pointerMinutes - taskStart),
    previewStart: originZone === 'timeline' ? taskStart : null,
    previewEnd: originZone === 'timeline' ? taskEnd : null,
    active: false,
  }
  event.currentTarget?.setPointerCapture?.(event.pointerId)
  document.addEventListener('pointermove', handlePointerDragMove, { passive: false })
  document.addEventListener('pointerup', handlePointerDragEnd)
  document.addEventListener('pointercancel', cancelPointerDrag)
}
function applyPointerDragPosition(clientX, clientY, pointerId) {
  const state = pointerDrag.value
  if (!state || state.pointerId !== pointerId) return
  const distance = Math.hypot(clientX - state.startX, clientY - state.startY)
  if (!state.active && distance < 8) return
  if (!state.active) {
    state.active = true
    draggingTask.value = state.task
    suppressTaskClick.value = true
    timelineError.value = ''
    document.body.classList.add('timeline-pointer-dragging')
  }
  updatePointerDragTarget(clientX, clientY)
}
function handlePointerDragMove(event) {
  const state = pointerDrag.value
  if (!state || state.pointerId !== event.pointerId) return
  event.preventDefault()
  pendingPointerDragPosition = {
    clientX: event.clientX,
    clientY: event.clientY,
    pointerId: event.pointerId,
  }
  if (pointerDragFrame) return
  pointerDragFrame = window.requestAnimationFrame(() => {
    pointerDragFrame = null
    const position = pendingPointerDragPosition
    pendingPointerDragPosition = null
    if (position) applyPointerDragPosition(position.clientX, position.clientY, position.pointerId)
  })
}
function flushPointerDragPosition(clientX, clientY, pointerId) {
  if (pointerDragFrame) {
    window.cancelAnimationFrame(pointerDragFrame)
    pointerDragFrame = null
  }
  pendingPointerDragPosition = null
  applyPointerDragPosition(clientX, clientY, pointerId)
}
async function handlePointerDragEnd(event) {
  const state = pointerDrag.value
  if (!state || state.pointerId !== event.pointerId) return
  flushPointerDragPosition(event.clientX, event.clientY, event.pointerId)
  const wasActive = state.active
  if (wasActive) {
    event.preventDefault()
    const task = state.task
    const zone = dragOverZone.value
    const startMinutes = state.previewStart ?? timelineDragMinutes.value
    const previewEnd = state.previewEnd
    pointerDrag.value = null
    removePointerDragListeners()
    clearDrag()
    if (zone === 'timeline' && startMinutes !== null) {
      const duration = previewEnd !== null && previewEnd !== undefined
        ? Math.max(15, previewEnd - startMinutes)
        : null
      await saveTaskSchedule(task, startMinutes, duration ? startMinutes + duration : null)
    } else if (zone === 'todo' && state.originZone !== 'todo') {
      timelineDragDraft.value = null
      if (timelineElementPreview) restoreTimelineElementPreview()
      await removeTaskFromTimeline(task)
    } else if (zone === 'urgent' || zone === 'completed') {
      timelineDragDraft.value = null
      if (timelineElementPreview) restoreTimelineElementPreview()
      await applyDropZoneAction(task, zone)
    } else {
      timelineDragDraft.value = null
      if (timelineElementPreview) restoreTimelineElementPreview()
    }
    window.clearTimeout(suppressClickTimer)
    suppressClickTimer = window.setTimeout(() => {
      suppressTaskClick.value = false
    }, 250)
    return
  }
  cancelPointerDrag()
}
function removePointerDragListeners() {
  document.removeEventListener('pointermove', handlePointerDragMove)
  document.removeEventListener('pointerup', handlePointerDragEnd)
  document.removeEventListener('pointercancel', cancelPointerDrag)
  if (pointerDragFrame) {
    window.cancelAnimationFrame(pointerDragFrame)
    pointerDragFrame = null
  }
  pendingPointerDragPosition = null
  document.body.classList.remove('timeline-pointer-dragging')
  stopPageAutoScroll()
  stopTimelineAutoScroll()
  clearPointerDropGeometries()
}
function cancelPointerDrag() {
  const wasActive = pointerDrag.value?.active
  pointerDrag.value = null
  timelineDragDraft.value = null
  removePointerDragListeners()
  if (wasActive) {
    clearDrag()
    window.clearTimeout(suppressClickTimer)
    suppressClickTimer = window.setTimeout(() => {
      suppressTaskClick.value = false
    }, 250)
  }
}
function handleTimelineDragOver(event) {
  event.preventDefault()
  if (dragOverZone.value !== 'timeline') dragOverZone.value = 'timeline'
  const nextMinutes = timelineMinutesFromEvent(event)
  if (timelineDragMinutes.value !== nextMinutes) timelineDragMinutes.value = nextMinutes
}
function handleTodoDragOver(event) {
  event.preventDefault()
  if (dragOverZone.value !== 'todo') dragOverZone.value = 'todo'
  if (timelineDragMinutes.value !== null) timelineDragMinutes.value = null
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = draggingTask.value?.kind === 'personal' ? 'move' : 'none'
  }
}
function scheduleIso(minutes) {
  return `${today.value}T${minutesToTime(minutes)}`
}
async function saveTaskSchedule(task, startMinutes, endMinutes = null) {
  timelineError.value = ''
  try {
    const data = await updateDeadlineState(task, {
      plannedStart: scheduleIso(startMinutes),
      plannedEnd: endMinutes ? scheduleIso(endMinutes) : null,
    }, { refresh: false })
    // Timeline items are computed copies. Update the canonical task in the
    // source array before Vue gets a chance to restore the old layout.
    const sourceTask = tasks.value.find((item) => item.id === task.id)
    if (sourceTask && data) Object.assign(sourceTask, data)
    await nextTick()
    finishTimelineElementPreview()
    // Coalesce stats/check-in refreshes so repeated timeline edits do not
    // compete with the next interaction for the render queue.
    scheduleDashboardRefresh()
    return true
  } catch (error) {
    timelineError.value = error.message || '保存时间安排失败'
    if (timelineElementPreview) restoreTimelineElementPreview()
    return false
  } finally {
    timelineDragDraft.value = null
  }
}
async function dropOnTimeline(event) {
  if (!draggingTask.value || !timelineBoardRef.value) return
  const task = draggingTask.value
  const duration = hasTimelineDuration(task)
    ? Math.max(15, timelineEndMinutes(task) - timelineStartMinutes(task))
    : null
  const startMinutes = timelineMinutesFromEvent(event, task)
  if (startMinutes === null) {
    clearDrag()
    return
  }
  draggingTask.value = null
  dragOverZone.value = ''
  timelineDragMinutes.value = null
  await saveTaskSchedule(task, startMinutes, duration ? startMinutes + duration : null)
}
async function dropOnTodo() {
  const task = draggingTask.value
  if (!task) return
  await removeTaskFromTimeline(task)
}
async function removeTaskFromTimeline(task) {
  draggingTask.value = null
  dragOverZone.value = ''
  timelineDragMinutes.value = null
  timelineDragDraft.value = null
  if (task.kind !== 'personal') {
    timelineError.value = '官方 DDL 会自动保留在时间轴上，不能摘除。'
    return
  }
  timelineError.value = ''
  try {
    await updateDeadlineState(task, { plannedStart: null, plannedEnd: null })
  } catch (error) {
    timelineError.value = error.message || '移出时间轴失败'
  }
}
async function applyDropZoneAction(task, zone) {
  if (!task) return
  try {
    if (zone === 'urgent') {
      await updateDeadlineState(task, { priority: 'high', done: false })
    }
    if (zone === 'completed') {
      await updateDeadlineState(task, { done: true })
    }
  } catch (error) {
    timelineError.value = error.message || '保存任务状态失败'
  }
}
async function restoreTaskToPoint(task) {
  if (!task?.plannedStart) return
  timelineError.value = ''
  try {
    await updateDeadlineState(task, {
      plannedStart: task.plannedStart.iso,
      plannedEnd: null,
    })
  } catch (error) {
    timelineError.value = error.message || '还原时间节点失败'
  }
}
function startResize(task, event) {
  if (!timelineBoardRef.value) return
  if (event.button !== undefined && event.button !== 0) return
  if (timelineStartMinutes(task) + 15 > 1440) {
    timelineError.value = '当天最后一个时间节点无法再延长。'
    return
  }
  event.preventDefault()
  document.body.classList.add('timeline-resizing')
  resizingTask.value = task
  resizePointerId = event.pointerId ?? null
  resizeDraft.value = {
    id: task.id,
    start: timelineStartMinutes(task),
    end: timelineEndMinutes(task),
  }
  resizeSession = {
    task,
    element: event.currentTarget?.closest?.('.axis-task') || null,
    start: timelineStartMinutes(task),
    end: timelineEndMinutes(task),
    originalHeight: event.currentTarget?.closest?.('.axis-task')?.style?.height || '',
    timeNodes: event.currentTarget?.closest?.('.axis-task')?.querySelectorAll?.('.axis-task-time'),
    durationNode: event.currentTarget?.closest?.('.axis-task')?.querySelector?.('.axis-task-duration'),
  }
  event.currentTarget?.setPointerCapture?.(event.pointerId)
  document.addEventListener('pointermove', handleResizeMove, { passive: false })
  document.addEventListener('pointerup', finishResize)
  document.addEventListener('pointercancel', cancelResize)
}
function applyResizePosition(clientY) {
  if (
    !resizingTask.value
    || !resizeSession
    || !timelineBoardRef.value
  ) return
  const rect = adjustedPointerRect(pointerDropGeometries?.timeline)
    || timelineBoardRef.value.getBoundingClientRect()
  const rawMinutes = ((clientY - rect.top + timelineBoardRef.value.scrollTop - timelineHeaderHeight) / timelineHourHeight) * 60
  const end = Math.max(
    resizeSession.start + 15,
    Math.min(1440, Math.round(rawMinutes / 15) * 15),
  )
  if (resizeSession.end === end) return
  resizeSession.end = end
  if (resizeSession.element) {
    resizeSession.element.style.height = `${Math.max(60, ((end - resizeSession.start) / 60) * timelineHourHeight)}px`
    setTimelineElementText(
      resizeSession.element,
      resizeSession.start,
      end,
      resizeSession.timeNodes,
      resizeSession.durationNode,
    )
  }
}
function handleResizeMove(event) {
  if (
    !resizingTask.value
    || !resizeDraft.value
    || (resizePointerId !== null && event.pointerId !== resizePointerId)
  ) return
  event.preventDefault()
  pendingResizeClientY = event.clientY
  if (resizeMoveFrame) return
  resizeMoveFrame = window.requestAnimationFrame(() => {
    resizeMoveFrame = null
    const clientY = pendingResizeClientY
    pendingResizeClientY = null
    if (clientY !== null) applyResizePosition(clientY)
  })
}
function flushResizePosition(clientY = pendingResizeClientY) {
  if (resizeMoveFrame) {
    window.cancelAnimationFrame(resizeMoveFrame)
    resizeMoveFrame = null
  }
  pendingResizeClientY = null
  if (clientY !== null && clientY !== undefined) applyResizePosition(clientY)
}
async function finishResize(event) {
  if (!resizingTask.value || !resizeSession) return
  if (resizePointerId !== null && event?.pointerId !== undefined && event.pointerId !== resizePointerId) return
  event?.preventDefault()
  flushResizePosition(event?.clientY)
  const task = resizingTask.value
  const draft = {
    start: resizeSession.start,
    end: resizeSession.end,
  }
  resizeDraft.value = { ...resizeDraft.value, end: draft.end }
  document.removeEventListener('pointermove', handleResizeMove)
  document.removeEventListener('pointerup', finishResize)
  document.removeEventListener('pointercancel', cancelResize)
  resizePointerId = null
  document.body.classList.remove('timeline-resizing')
  resizingTask.value = null
  const saved = await saveTaskSchedule(task, draft.start, draft.end)
  if (!saved && resizeSession) {
    if (resizeSession.element) {
      resizeSession.element.style.height = resizeSession.originalHeight
      setTimelineElementText(
        resizeSession.element,
        resizeSession.start,
        timeToMinutes(task.plannedEnd?.time) || resizeSession.start + 15,
        resizeSession.timeNodes,
        resizeSession.durationNode,
      )
    }
  }
  resizeSession = null
  resizeDraft.value = null
}
function cancelResize() {
  document.removeEventListener('pointermove', handleResizeMove)
  document.removeEventListener('pointerup', finishResize)
  document.removeEventListener('pointercancel', cancelResize)
  if (resizeMoveFrame) {
    window.cancelAnimationFrame(resizeMoveFrame)
    resizeMoveFrame = null
  }
  pendingResizeClientY = null
  resizePointerId = null
  document.body.classList.remove('timeline-resizing')
  if (resizeSession?.element) {
    resizeSession.element.style.height = resizeSession.originalHeight
    setTimelineElementText(
      resizeSession.element,
      resizeSession.start,
      resizeSession.end,
      resizeSession.timeNodes,
      resizeSession.durationNode,
    )
  }
  resizeSession = null
  resizingTask.value = null
  resizeDraft.value = null
}
async function dropToZone(zone) {
  if (!draggingTask.value) return
  const task = draggingTask.value
  draggingTask.value = null
  dragOverZone.value = ''
  timelineDragMinutes.value = null
  await applyDropZoneAction(task, zone)
}
function clearDrag(event = null) {
  if (
    event?.currentTarget
    && event.relatedTarget
    && event.currentTarget.contains(event.relatedTarget)
  ) return
  draggingTask.value = null
  dragOverZone.value = ''
  timelineDragMinutes.value = null
}
function clearDragOver(event = null) {
  if (
    event?.currentTarget
    && event.relatedTarget
    && event.currentTarget.contains(event.relatedTarget)
  ) return
  dragOverZone.value = ''
  timelineDragMinutes.value = null
}
function taskReminderValue(task) {
  return task?.reminders?.map((item) => `${item.date}T${item.time}`) || []
}
function taskEditorDuration() {
  if (!taskEditor.value.plannedStart) return 0
  const start = timeToMinutes(taskEditor.value.plannedStart)
  const end = taskEditorEndsAtMidnight.value ? 1440 : timeToMinutes(taskEditor.value.plannedEnd)
  if (start === null || end === null) return 0
  return Math.max(0, end - start)
}
function openTask(task, edit = activeView.value !== '日历') {
  selectedTask.value = task
  taskEditorError.value = ''
  taskEditorEndsAtMidnight.value = task.plannedEnd?.time === '24:00'
  taskEditor.value = {
    status: task.status || (task.done ? 'done' : 'todo'),
    priority: task.priority || 'normal',
    note: task.note || '',
    reminders: taskReminderValue(task),
    planDate: task.plannedStart?.date || task.date || today.value,
    plannedStart: task.plannedStart?.time || '',
    plannedEnd: task.plannedEnd?.time === '24:00' ? '' : task.plannedEnd?.time || '',
  }
  taskEditorOpen.value = edit
}
function openTaskFromPointer(task) {
  if (suppressTaskClick.value) {
    suppressTaskClick.value = false
    return
  }
  openTask(task)
}
function openGlobalSearch() {
  globalQuery.value = ''
  showGlobalSearch.value = true
}
function closeGlobalSearch() {
  showGlobalSearch.value = false
  globalQuery.value = ''
}
function handleGlobalKeydown(event) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    openGlobalSearch()
  } else if (event.key === 'Escape' && chatImageViewer.value) {
    closeChatImage()
  } else if (event.key === 'Escape' && showGlobalSearch.value) {
    closeGlobalSearch()
  }
}
function openGlobalSearchTask(task) {
  closeGlobalSearch()
  activeView.value = '日历'
  selectCalendarDate(task.date, task)
  openTask(task, false)
}
function openGlobalSearchSubscription(item) {
  closeGlobalSearch()
  activeView.value = '订阅中心'
  filter.value = '全部'
  query.value = item.name
}
function addReminder() {
  taskEditor.value.reminders.push('')
}
function removeReminder(index) {
  taskEditor.value.reminders.splice(index, 1)
}
async function saveTaskDetails() {
  if (!selectedTask.value) return
  taskEditorError.value = ''
  taskEditorSaving.value = true
  try {
    await updateDeadlineState(selectedTask.value, {
      status: taskEditor.value.status,
      priority: taskEditor.value.priority,
      note: taskEditor.value.note,
      plannedStart: taskEditor.value.plannedStart
        ? `${taskEditor.value.planDate || selectedTask.value.date}T${taskEditor.value.plannedStart}`
        : null,
      plannedEnd: taskEditorEndsAtMidnight.value
        ? `${taskEditor.value.planDate || selectedTask.value.date}T24:00`
        : taskEditor.value.plannedEnd
        ? `${taskEditor.value.planDate || selectedTask.value.date}T${taskEditor.value.plannedEnd}`
        : null,
      reminders: taskEditor.value.reminders.filter(Boolean),
    })
    taskEditorOpen.value = false
  } catch (error) {
    taskEditorError.value = error.message || '保存我的安排失败'
  } finally {
    taskEditorSaving.value = false
  }
}
async function toggleSubscription(item) {
  subscriptionError.value = ''
  if (!item.subscribed && item.courseStatus === 'ended') {
    subscriptionError.value = '该课程已结束，不能重新订阅。'
    return
  }
  if (!item.subscribed && item.courseSubscribed) {
    subscriptionError.value = `你已经订阅了该课程的${item.currentClassName || '其他班级'}，如需更换请先取消原订阅。`
    return
  }
  const response = await apiFetch(`/api/subscriptions/${item.classId}/toggle/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (response.ok) {
    await loadBootstrap()
  } else {
    const data = await response.json()
    subscriptionError.value = data.error || '订阅操作失败'
  }
}
function resetPersonalTaskForm(dueDate = today.value) {
  editingPersonalTask.value = null
  newTask.value = { title: '', due: dueDate, dueTime: '23:59', note: '' }
}
function openPersonalTaskCreate(dueDate = today.value) {
  resetPersonalTaskForm(dueDate)
  showCreate.value = true
}
function toggleHomeLike(post) {
  post.liked = !post.liked
  post.likes += post.liked ? 1 : -1
  homeLikedPostIds.value = post.liked
    ? [...homeLikedPostIds.value, post.id]
    : homeLikedPostIds.value.filter((id) => id !== post.id)
}
function toggleHomeSave(post) {
  post.saved = !post.saved
  homeSavedPostIds.value = post.saved
    ? [...homeSavedPostIds.value, post.id]
    : homeSavedPostIds.value.filter((id) => id !== post.id)
}
function toggleHomeFollow(post) {
  post.followed = !post.followed
  homeFollowedUserIds.value = post.followed
    ? [...homeFollowedUserIds.value, post.author]
    : homeFollowedUserIds.value.filter((id) => id !== post.author)
}
function toggleHomeGroup(group) {
  group.joined = !group.joined
  homeJoinedGroupIds.value = group.joined
    ? [...homeJoinedGroupIds.value, group.id]
    : homeJoinedGroupIds.value.filter((id) => id !== group.id)
}
function toggleHomeEvent(event) {
  event.joined = !event.joined
}
function setFriendTab(tab) {
  friendTab.value = tab
  friendQuery.value = ''
}
async function loadFriends() {
  if (!isAuthenticated.value || authRole.value !== 'student') return
  friendsLoading.value = true
  friendsError.value = ''
  try {
    const response = await apiFetch('/api/friends/')
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '加载好友列表失败')
    if (data.users?.length) friendUsers.value = data.users
  } catch (error) {
    friendsError.value = error.message
  } finally {
    friendsLoading.value = false
  }
}
async function runFriendAction(user, action) {
  if (typeof user.id !== 'number') {
    if (action === 'request' && user.status === 'not_friend') user.status = 'pending_sent'
    if (action === 'accept' && user.status === 'pending_received') user.status = 'friend'
    if (action === 'reject' && user.status === 'pending_received') user.status = 'not_friend'
    if (action === 'cancel' && user.status === 'pending_sent') user.status = 'not_friend'
    if (action === 'delete' && user.status === 'friend') user.status = 'not_friend'
    return
  }
  try {
    const response = await apiFetch(`/api/friends/${user.id}/${action}/`, { method: 'POST' })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '好友操作失败')
    Object.assign(user, data.user)
  } catch (error) {
    friendsError.value = error.message
  }
}
async function sendFriendRequest(user) {
  await runFriendAction(user, 'request')
}
async function acceptFriendRequest(user) {
  await runFriendAction(user, 'accept')
}
async function rejectFriendRequest(user) {
  await runFriendAction(user, 'reject')
}
async function cancelFriendRequest(user) {
  await runFriendAction(user, 'cancel')
}
async function removeFriend(user) {
  if (!window.confirm(`确定删除好友“${user.name}”吗？`)) return
  await runFriendAction(user, 'delete')
}
async function loadChats() {
  if (!isAuthenticated.value || authRole.value !== 'student') return
  chatsLoading.value = true
  chatError.value = ''
  try {
    const response = await apiFetch('/api/chats/')
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '加载消息列表失败')
    chats.value = data.chats?.length
      ? data.chats.map(normalizeChat)
      : chats.value.filter((chat) => typeof chat.userId !== 'number')
  } catch (error) {
    chatError.value = error.message
  } finally {
    chatsLoading.value = false
  }
}
async function loadChatGroups() {
  if (!isAuthenticated.value || authRole.value !== 'student') return
  chatGroupLoading.value = true
  try {
    const response = await apiFetch('/api/chat-groups/')
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '加载学习小组失败')
    chatGroups.value = data.groups || []
    chatGroupInvitations.value = data.invitations || []
  } catch (error) {
    chatError.value = error.message
  } finally {
    chatGroupLoading.value = false
  }
}
async function loadChatGroupInviteOptions() {
  if (!chatGroup.value) return
  chatGroupInviteLoading.value = true
  chatGroupInviteError.value = ''
  try {
    const response = await apiFetch(`/api/chat-groups/${chatGroup.value.id}/invites/`)
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '加载可邀请好友失败')
    chatGroupInviteCandidates.value = data.candidates || []
    chatGroupPendingInvitations.value = data.pending || []
  } catch (error) {
    chatGroupInviteError.value = error.message
  } finally {
    chatGroupInviteLoading.value = false
  }
}
async function openChatGroupInvite() {
  if (!chatGroup.value) return
  chatGroupInviteOpen.value = true
  chatGroupInviteCandidates.value = []
  chatGroupPendingInvitations.value = []
  await loadChatGroupInviteOptions()
}
async function inviteChatGroupFriend(friend) {
  if (!chatGroup.value || friend.pending || chatGroupInviteSendingIds.value.includes(friend.id)) return
  chatGroupInviteSendingIds.value = [...chatGroupInviteSendingIds.value, friend.id]
  chatGroupInviteError.value = ''
  try {
    const response = await apiFetch(`/api/chat-groups/${chatGroup.value.id}/invites/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ targetId: friend.id }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '发送邀请失败')
    await loadChatGroupInviteOptions()
  } catch (error) {
    chatGroupInviteError.value = error.message
  } finally {
    chatGroupInviteSendingIds.value = chatGroupInviteSendingIds.value.filter((id) => id !== friend.id)
  }
}
async function respondChatGroupInvitation(invitation, action) {
  chatError.value = ''
  try {
    const response = await apiFetch(`/api/chat-group-invites/${invitation.id}/${action}/`, {
      method: 'POST',
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '处理邀请失败')
    chatGroupInvitations.value = chatGroupInvitations.value.filter((item) => item.id !== invitation.id)
    await loadChatGroups()
    if (action === 'accept') await openChatGroup(data.group)
  } catch (error) {
    chatError.value = error.message
  }
}
async function openChatGroup(group) {
  chatMode.value = 'groups'
  closeChatSocket()
  chatGroup.value = group
  chatGroupMessagesLoading.value = true
  chatError.value = ''
  try {
    const response = await apiFetch(`/api/chat-groups/${group.id}/messages/`)
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '加载小组消息失败')
    chatGroup.value = data.group
    chatGroupMessages.value = data.messages || []
    const index = chatGroups.value.findIndex((item) => item.id === group.id)
    if (index >= 0) chatGroups.value[index] = data.group
    scrollChatGroupToBottom()
    connectChatGroupSocket(data.group)
  } catch (error) {
    chatError.value = error.message
  } finally {
    chatGroupMessagesLoading.value = false
  }
}
async function createChatGroup() {
  const payload = {
    name: newChatGroup.value.name.trim(),
    kind: newChatGroup.value.kind,
    description: newChatGroup.value.description.trim(),
  }
  if (!payload.name) return
  const response = await apiFetch('/api/chat-groups/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await response.json()
  if (!response.ok) {
    chatError.value = data.error || '创建小组失败'
    return
  }
  chatGroups.value = [data.group, ...chatGroups.value]
  newChatGroup.value = { name: '', kind: 'learning', description: '' }
  chatGroupFormOpen.value = false
  await openChatGroup(data.group)
}
async function toggleChatGroupMembership(group) {
  const action = group.joined ? 'leave' : 'join'
  const response = await apiFetch(`/api/chat-groups/${group.id}/${action}/`, { method: 'POST' })
  const data = await response.json()
  if (!response.ok) {
    chatError.value = data.error || '小组操作失败'
    return
  }
  const index = chatGroups.value.findIndex((item) => item.id === group.id)
  if (index >= 0) chatGroups.value[index] = data.group
  if (chatGroup.value?.id === group.id) {
    if (action === 'leave') {
      closeChatGroupSocket()
      chatGroup.value = null
      chatGroupMessages.value = []
    } else {
      await openChatGroup(data.group)
    }
  }
}
async function sendChatGroupMessage() {
  const content = chatGroupDraft.value.trim()
  if (
    (!content && !chatGroupImageFile.value && !chatGroupAttachmentFile.value && !chatGroupSharedTask.value)
    || !chatGroup.value
    || !chatGroup.value.joined
    || chatGroupSending.value
  ) return
  chatGroupSending.value = true
  chatGroupUploadState.value = chatGroupImageFile.value || chatGroupAttachmentFile.value ? 'uploading' : 'idle'
  chatGroupUploadProgress.value = 0
  chatError.value = ''
  try {
    const formData = new FormData()
    formData.append('content', content)
    if (chatGroupImageFile.value) formData.append('image', chatGroupImageFile.value)
    if (chatGroupAttachmentFile.value) formData.append('attachment', chatGroupAttachmentFile.value)
    if (chatGroupSharedTask.value) {
      formData.append('shareType', chatGroupSharedTask.value.type)
      formData.append('shareId', String(chatGroupSharedTask.value.id))
    }
    const hasUpload = Boolean(chatGroupImageFile.value || chatGroupAttachmentFile.value)
    const data = hasUpload
      ? await uploadChatMessage(
        `/api/chat-groups/${chatGroup.value.id}/messages/`,
        formData,
        chatGroupUploadProgress,
      )
      : await (async () => {
        const response = await apiFetch(`/api/chat-groups/${chatGroup.value.id}/messages/`, {
          method: 'POST',
          body: formData,
        })
        const result = await response.json()
        if (!response.ok) throw new Error(result.error || '发送群消息失败')
        return result
      })()
    if (!chatGroupMessages.value.some((message) => message.id === data.message.id)) {
      chatGroupMessages.value = [...chatGroupMessages.value, data.message]
    }
    chatGroup.value = data.group
    chatGroupDraft.value = ''
    clearChatGroupImage()
    clearChatGroupAttachment()
    clearChatGroupTask()
    scrollChatGroupToBottom()
  } catch (error) {
    chatError.value = error.message
    if (chatGroupImageFile.value || chatGroupAttachmentFile.value) {
      chatGroupUploadState.value = 'failed'
    }
  } finally {
    chatGroupSending.value = false
  }
}
async function loadChatMessages(peer = chatPeer.value, { silent = false } = {}) {
  if (!peer) return
  chatPeer.value = peer
  if (!silent) chatMessagesLoading.value = true
  chatError.value = ''
  try {
    if (typeof peer.userId !== 'number') {
      chatMessages.value = demoChatMessages.value[peer.userId] || []
      peer.unread = 0
      scrollChatToBottom()
      return
    }
    const response = await apiFetch(`/api/chats/${peer.userId}/messages/`)
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '加载聊天记录失败')
    const normalizedPeer = normalizeChat(data.peer)
    chatPeer.value = normalizedPeer
    const index = chats.value.findIndex((chat) => chat.userId === peer.userId)
    if (index >= 0) chats.value[index] = normalizedPeer
    chatMessages.value = data.messages || []
    scrollChatToBottom()
  } catch (error) {
    chatError.value = error.message
  } finally {
    if (!silent) chatMessagesLoading.value = false
  }
}
async function openChat(chat) {
  activeView.value = '消息'
  closeChatGroupSocket()
  chatPeer.value = chat
  chatMessageQuery.value = ''
  chatMessageSearchOpen.value = false
  await loadChatMessages(chat)
  connectChatSocket(chat)
}
function closeChatSocket() {
  if (chatSocketReconnectTimer) {
    window.clearTimeout(chatSocketReconnectTimer)
    chatSocketReconnectTimer = null
  }
  if (chatSocket) {
    chatSocket.onclose = null
    chatSocket.close()
    chatSocket = null
  }
  chatSocketPeerId = null
}
function closeChatGroupSocket() {
  if (chatGroupSocketReconnectTimer) {
    window.clearTimeout(chatGroupSocketReconnectTimer)
    chatGroupSocketReconnectTimer = null
  }
  if (chatGroupSocket) {
    chatGroupSocket.onclose = null
    chatGroupSocket.close()
    chatGroupSocket = null
  }
  chatGroupSocketId = null
}
function connectChatSocket(peer) {
  closeChatSocket()
  if (!peer || typeof peer.userId !== 'number' || !window.WebSocket) return
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/chats/${peer.userId}/`)
  chatSocket = socket
  chatSocketPeerId = peer.userId
  socket.onmessage = (event) => {
    let data
    try {
      data = JSON.parse(event.data)
    } catch {
      return
    }
    if (data.type !== 'message' || chatSocket !== socket || chatPeer.value?.userId !== peer.userId) return
    if (chatMessages.value.some((message) => message.id === data.message?.id)) return
    chatMessages.value = [...chatMessages.value, data.message]
    chatPeer.value.lastMessage = data.message.content
      || (data.message.imageUrl ? '图片' : data.message.taskCard ? '任务' : '')
    chatPeer.value.lastAt = data.message.time || '刚刚'
    if (data.notification) {
      const existing = notifications.value.find((item) => item.id === data.notification.id)
      if (existing) {
        Object.assign(existing, data.notification, { read: true })
      } else {
        notifications.value = [
          { ...data.notification, read: true },
          ...notifications.value,
        ].slice(0, 50)
      }
      markNotificationsRead([data.notification.id]).catch(() => {})
    }
    scrollChatToBottom()
  }
  socket.onclose = () => {
    if (chatSocket !== socket || activeView.value !== '消息' || chatPeer.value?.userId !== peer.userId) return
    chatSocket = null
    chatSocketReconnectTimer = window.setTimeout(() => connectChatSocket(chatPeer.value), 3000)
  }
  socket.onerror = () => socket.close()
}
function connectChatGroupSocket(group) {
  closeChatGroupSocket()
  if (!group?.joined || typeof group.id !== 'number' || !window.WebSocket) return
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/chat-groups/${group.id}/`)
  chatGroupSocket = socket
  chatGroupSocketId = group.id
  socket.onmessage = (event) => {
    let data
    try {
      data = JSON.parse(event.data)
    } catch {
      return
    }
    if (data.type !== 'message' || chatGroupSocket !== socket || chatGroup.value?.id !== group.id) return
    if (chatGroupMessages.value.some((message) => message.id === data.message?.id)) return
    chatGroupMessages.value = [...chatGroupMessages.value, data.message]
    chatGroup.value.lastMessage = data.message.content
      || (data.message.imageUrl ? '图片' : data.message.taskCard ? '任务' : '文件')
    chatGroup.value.lastAt = data.message.time || '刚刚'
    const index = chatGroups.value.findIndex((item) => item.id === group.id)
    if (index >= 0) chatGroups.value[index] = { ...chatGroups.value[index], ...chatGroup.value }
    scrollChatGroupToBottom()
  }
  socket.onclose = () => {
    if (chatGroupSocket !== socket || activeView.value !== '消息' || chatGroup.value?.id !== group.id) return
    chatGroupSocket = null
    chatGroupSocketReconnectTimer = window.setTimeout(
      () => connectChatGroupSocket(chatGroup.value),
      3000,
    )
  }
  socket.onerror = () => socket.close()
}
watch(activeView, (view) => {
  if (view !== '消息') {
    closeChatSocket()
    closeChatGroupSocket()
  }
})
function toggleChatMessageSearch() {
  chatMessageSearchOpen.value = !chatMessageSearchOpen.value
  if (!chatMessageSearchOpen.value) chatMessageQuery.value = ''
}
function taskCardFromTask(task) {
  return {
    type: task.deadlineId ? 'deadline' : 'personal',
    id: task.deadlineId || task.personalTaskId,
    title: task.title,
    date: task.date,
    time: task.time,
    source: task.source,
    sourceName: task.sourceName,
  }
}
function selectChatTask(task) {
  chatSharedTask.value = taskCardFromTask(task)
  chatTaskPickerOpen.value = false
  chatError.value = ''
}
function clearChatTask() {
  chatSharedTask.value = null
}
function openSharedTaskCard(card) {
  if (!card) return
  const task = tasks.value.find((item) => (
    card.type === 'deadline'
      ? item.deadlineId === card.id
      : item.personalTaskId === card.id
  ))
  if (task) openTask(task)
}
function toggleChatMessageActions(message) {
  chatMessageActionId.value = chatMessageActionId.value === message.id ? null : message.id
}
function deleteChatMessageLocally(message) {
  chatHiddenMessageIds.value = [...chatHiddenMessageIds.value, message.id]
  chatMessageActionId.value = null
}
async function recallChatMessage(message) {
  if (typeof message.id !== 'number') {
    message.recalled = true
    message.content = '消息已撤回'
    message.imageUrl = ''
    chatMessageActionId.value = null
    return
  }
  try {
    const response = await apiFetch(`/api/chat-messages/${message.id}/recall/`, { method: 'POST' })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '撤回消息失败')
    const index = chatMessages.value.findIndex((item) => item.id === message.id)
    if (index >= 0) chatMessages.value[index] = data.message
    chatMessageActionId.value = null
  } catch (error) {
    chatError.value = error.message
  }
}
async function toggleChatMute() {
  if (!chatPeer.value) return
  if (typeof chatPeer.value.userId !== 'number') {
    chatPeer.value.muted = !chatPeer.value.muted
    return
  }
  try {
    const response = await apiFetch(`/api/chats/${chatPeer.value.userId}/mute/`, { method: 'POST' })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '设置免打扰失败')
    chatPeer.value = normalizeChat(data.peer)
    const index = chats.value.findIndex((chat) => chat.userId === chatPeer.value.userId)
    if (index >= 0) chats.value[index] = chatPeer.value
  } catch (error) {
    chatError.value = error.message
  }
}
async function blockChatPeer() {
  if (!chatPeer.value || !window.confirm(`确定拉黑“${chatPeer.value.name}”吗？`)) return
  if (typeof chatPeer.value.userId !== 'number') {
    chats.value = chats.value.filter((chat) => chat.userId !== chatPeer.value.userId)
  } else {
    const response = await apiFetch(`/api/chats/${chatPeer.value.userId}/block/`, { method: 'POST' })
    const data = await response.json()
    if (!response.ok) {
      chatError.value = data.error || '拉黑失败'
      return
    }
    await loadChats()
  }
  chatPeer.value = null
  chatMessages.value = []
}
async function reportChatPeer() {
  if (!chatPeer.value) return
  const reason = window.prompt('请填写举报原因')
  if (!reason?.trim() || typeof chatPeer.value.userId !== 'number') return
  const response = await apiFetch(`/api/chats/${chatPeer.value.userId}/report/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: reason.trim() }),
  })
  const data = await response.json()
  if (!response.ok) {
    chatError.value = data.error || '举报失败'
    return
  }
  window.alert('举报已提交，我们会尽快处理。')
}
async function openChatWithUser(user) {
  if (user.status !== 'friend') return
  const existing = chats.value.find((chat) => chat.userId === user.id)
  await openChat(existing || { ...user, userId: user.id, unread: 0, lastMessage: '', lastAt: '' })
}
function clearChatImage({ revoke = true } = {}) {
  if (revoke && chatImagePreview.value) {
    URL.revokeObjectURL(chatImagePreview.value)
  }
  chatImageFile.value = null
  chatImagePreview.value = ''
  chatUploadState.value = 'idle'
  chatUploadProgress.value = 0
  if (chatImageInputRef.value) chatImageInputRef.value.value = ''
}
function clearChatAttachment() {
  chatAttachmentFile.value = null
  chatAttachment.value = null
  if (chatAttachmentInputRef.value) chatAttachmentInputRef.value.value = ''
  if (!chatImageFile.value) {
    chatUploadState.value = 'idle'
    chatUploadProgress.value = 0
  }
}
function clearChatGroupImage({ revoke = true } = {}) {
  if (revoke && chatGroupImagePreview.value) {
    URL.revokeObjectURL(chatGroupImagePreview.value)
  }
  chatGroupImageFile.value = null
  chatGroupImagePreview.value = ''
  chatGroupUploadState.value = 'idle'
  chatGroupUploadProgress.value = 0
  if (chatGroupImageInputRef.value) chatGroupImageInputRef.value.value = ''
}
function clearChatGroupAttachment() {
  chatGroupAttachmentFile.value = null
  chatGroupAttachment.value = null
  if (chatGroupAttachmentInputRef.value) chatGroupAttachmentInputRef.value.value = ''
  if (!chatGroupImageFile.value) {
    chatGroupUploadState.value = 'idle'
    chatGroupUploadProgress.value = 0
  }
}
function selectChatGroupImage(file) {
  if (!file) return
  const acceptedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!acceptedTypes.includes(file.type)) {
    chatError.value = '仅支持 JPG、PNG、GIF 和 WEBP 图片。'
    clearChatGroupImage()
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    chatError.value = '图片不能超过 10MB。'
    clearChatGroupImage()
    return
  }
  clearChatGroupAttachment()
  clearChatGroupImage()
  chatGroupImageFile.value = file
  chatGroupImagePreview.value = URL.createObjectURL(file)
  chatError.value = ''
}
function selectChatGroupAttachment(file) {
  if (!file) return
  const extension = `.${file.name.split('.').pop()?.toLowerCase() || ''}`
  const acceptedExtensions = ['.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.mp3', '.wav', '.m4a', '.webm', '.ogg']
  if (!acceptedExtensions.includes(extension)) {
    chatError.value = '暂不支持该文件类型。'
    clearChatGroupAttachment()
    return
  }
  if (file.size > 50 * 1024 * 1024) {
    chatError.value = '文件不能超过 50MB。'
    clearChatGroupAttachment()
    return
  }
  clearChatGroupImage()
  clearChatGroupAttachment()
  chatGroupAttachmentFile.value = file
  chatGroupAttachment.value = {
    name: file.name,
    size: file.size,
    type: file.type,
  }
  chatError.value = ''
}
function clearChatGroupTask() {
  chatGroupSharedTask.value = null
}
function selectChatGroupTask(task) {
  chatGroupSharedTask.value = taskCardFromTask(task)
  chatGroupTaskPickerOpen.value = false
  chatError.value = ''
}
function stopChatRecordingStream() {
  chatRecorderStream?.getTracks().forEach((track) => track.stop())
  chatRecorderStream = null
}
function resetChatRecording() {
  if (chatRecordingTimer) {
    window.clearInterval(chatRecordingTimer)
    chatRecordingTimer = null
  }
  chatRecording.value = false
  chatRecordingSeconds.value = 0
  chatRecorder = null
  chatRecorderChunks = []
  stopChatRecordingStream()
}
function recordingTimeLabel() {
  const minutes = Math.floor(chatRecordingSeconds.value / 60)
  const seconds = chatRecordingSeconds.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}
function supportedRecordingMimeType() {
  if (!window.MediaRecorder) return ''
  return [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
  ].find((type) => window.MediaRecorder.isTypeSupported(type)) || ''
}
async function startChatRecording() {
  if (
    chatRecording.value
    || chatSending.value
    || !chatPeer.value
    || typeof chatPeer.value.userId !== 'number'
  ) return
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    chatRecordingError.value = '当前浏览器不支持录音，请使用文件按钮上传音频。'
    return
  }
  const mimeType = supportedRecordingMimeType()
  if (!mimeType) {
    chatRecordingError.value = '当前浏览器没有可用的录音格式，请使用文件按钮上传音频。'
    return
  }
  chatRecordingError.value = ''
  try {
    chatRecorderStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    chatRecorder = new MediaRecorder(chatRecorderStream, { mimeType })
    chatRecorderChunks = []
    chatRecorder.ondataavailable = (event) => {
      if (event.data.size) chatRecorderChunks.push(event.data)
    }
    chatRecorder.onstop = () => {
      const uploadMimeType = mimeType.split(';')[0]
      const extension = mimeType.includes('mp4')
        ? 'm4a'
        : mimeType.includes('ogg')
          ? 'ogg'
          : 'webm'
      const file = new File(
        chatRecorderChunks,
        `voice-${Date.now()}.${extension}`,
        { type: uploadMimeType },
      )
      resetChatRecording()
      selectChatAttachment(file)
    }
    chatRecorder.start()
    chatRecording.value = true
    chatRecordingSeconds.value = 0
    chatRecordingTimer = window.setInterval(() => {
      chatRecordingSeconds.value += 1
      if (chatRecordingSeconds.value >= 300) stopChatRecording()
    }, 1000)
  } catch (error) {
    resetChatRecording()
    chatRecordingError.value = error?.name === 'NotAllowedError'
      ? '录音权限被拒绝，请允许浏览器使用麦克风。'
      : '无法开始录音，请改用文件按钮上传音频。'
  }
}
function stopChatRecording() {
  if (!chatRecorder || chatRecorder.state === 'inactive') return
  chatRecorder.stop()
}
function cancelChatRecording() {
  if (!chatRecorder) return
  chatRecorder.onstop = null
  if (chatRecorder.state !== 'inactive') chatRecorder.stop()
  resetChatRecording()
}
function selectChatAttachment(file) {
  if (!file) return
  const extension = `.${file.name.split('.').pop()?.toLowerCase() || ''}`
  const acceptedExtensions = ['.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.mp3', '.wav', '.m4a', '.webm', '.ogg']
  if (!acceptedExtensions.includes(extension)) {
    chatError.value = '暂不支持该文件类型。'
    clearChatAttachment()
    return
  }
  if (file.size > 50 * 1024 * 1024) {
    chatError.value = '文件不能超过 50MB。'
    clearChatAttachment()
    return
  }
  clearChatImage()
  clearChatAttachment()
  chatAttachmentFile.value = file
  chatAttachment.value = {
    name: file.name,
    size: file.size,
    type: file.type,
  }
  chatError.value = ''
}
function handleChatAttachmentChange(event) {
  selectChatAttachment(event.target.files?.[0])
}
function selectChatImage(file) {
  if (!file) return
  const acceptedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!acceptedTypes.includes(file.type)) {
    chatError.value = '仅支持 JPG、PNG、GIF 和 WEBP 图片。'
    clearChatImage()
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    chatError.value = '图片不能超过 10MB。'
    clearChatImage()
    return
  }
  clearChatAttachment()
  clearChatImage()
  chatImageFile.value = file
  chatImagePreview.value = URL.createObjectURL(file)
  chatUploadState.value = 'idle'
  chatUploadProgress.value = 0
  chatError.value = ''
}
function handleChatImageChange(event) {
  selectChatImage(event.target.files?.[0])
}
function handleChatPaste(event) {
  const file = Array.from(event.clipboardData?.files || []).find((item) => item.type.startsWith('image/'))
  if (!file) return
  event.preventDefault()
  selectChatImage(file)
}
function handleChatDragOver(event) {
  if (!Array.from(event.dataTransfer?.items || []).some((item) => item.kind === 'file')) return
  event.dataTransfer.dropEffect = 'copy'
  chatImageDropActive.value = true
}
function handleChatDragLeave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    chatImageDropActive.value = false
  }
}
function handleChatDrop(event) {
  event.preventDefault()
  chatImageDropActive.value = false
  const file = Array.from(event.dataTransfer?.files || []).find((item) => item.type.startsWith('image/'))
  selectChatImage(file)
}
async function sendChatMessage() {
  const content = chatDraft.value.trim()
  if ((!content && !chatImageFile.value && !chatAttachmentFile.value && !chatSharedTask.value) || !chatPeer.value || chatSending.value) return
  chatSending.value = true
  chatUploadState.value = chatImageFile.value || chatAttachmentFile.value ? 'uploading' : 'idle'
  chatUploadProgress.value = 0
  chatError.value = ''
  try {
    if (typeof chatPeer.value.userId !== 'number') {
      const message = {
        id: `demo-message-${Date.now()}`,
        senderId: 'me',
        senderName: student.value.name,
        content,
        imageUrl: chatImagePreview.value,
        attachment: chatAttachment.value,
        taskCard: chatSharedTask.value,
        time: '刚刚',
        isMine: true,
        read: true,
      }
      const messages = demoChatMessages.value[chatPeer.value.userId] || []
      demoChatMessages.value[chatPeer.value.userId] = [...messages, message]
      chatMessages.value = demoChatMessages.value[chatPeer.value.userId]
      chatPeer.value.lastMessage = content || '图片'
      chatPeer.value.lastAt = '刚刚'
      clearChatImage({ revoke: false })
      clearChatAttachment()
      clearChatTask()
    } else {
      const formData = new FormData()
      formData.append('content', content)
      if (chatImageFile.value) formData.append('image', chatImageFile.value)
      if (chatAttachmentFile.value) formData.append('attachment', chatAttachmentFile.value)
      if (chatSharedTask.value) {
        formData.append('shareType', chatSharedTask.value.type)
        formData.append('shareId', String(chatSharedTask.value.id))
      }
      const hasUpload = Boolean(chatImageFile.value || chatAttachmentFile.value)
      const data = hasUpload
        ? await uploadChatMessage(`/api/chats/${chatPeer.value.userId}/messages/`, formData)
        : await (async () => {
          const response = await apiFetch(`/api/chats/${chatPeer.value.userId}/messages/`, {
            method: 'POST',
            body: formData,
          })
          const result = await response.json()
          if (!response.ok) throw new Error(result.error || '发送消息失败')
          return result
        })()
      chatMessages.value = [...chatMessages.value, data.message]
      scrollChatToBottom()
      chatPeer.value = normalizeChat(data.peer)
      const index = chats.value.findIndex((chat) => chat.userId === chatPeer.value.userId)
      if (index >= 0) chats.value[index] = chatPeer.value
      else chats.value.unshift(chatPeer.value)
      clearChatImage()
      clearChatAttachment()
      clearChatTask()
    }
    chatDraft.value = ''
  } catch (error) {
    chatError.value = error.message
    if (chatImageFile.value || chatAttachmentFile.value) chatUploadState.value = 'failed'
  } finally {
    chatSending.value = false
  }
}
function handleChatKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendChatMessage()
  }
}
function handleChatGroupKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendChatGroupMessage()
  }
}
function openFriendSpace(user) {
  friendProfile.value = user
}
function submitHomePost() {
  const body = homeComposerDraft.value.trim()
  if (!body) return
  communityPosts.value.unshift({
    id: `local-${Date.now()}`,
    author: student.value.name || '我',
    initials: (student.value.name || '我').slice(0, 1),
    school: student.value.school || '我的学校',
    grade: dashboard.value.identity.grade || '学生',
    time: '刚刚',
    scope: '我的学校',
    title: '分享一个学习现场',
    body,
    tags: ['我的分享'],
    likes: 0,
    comments: 0,
    liked: false,
    saved: false,
    followed: true,
    verified: false,
  })
  homeComposerDraft.value = ''
  homeComposerOpen.value = false
}
function openPersonalSpace() {
  activeView.value = '我的空间'
  personalSpaceTab.value = '动态'
}
function setPersonalSpaceTab(tab) {
  personalSpaceTab.value = tab
}
function togglePersonalPrivacy() {
  personalSpaceVisibility.value = personalSpaceVisibility.value === '仅自己'
    ? '交流圈可见'
    : personalSpaceVisibility.value === '交流圈可见'
      ? '公开'
      : '仅自己'
}
function setPersonalPrivacy(level) {
  personalSpaceVisibility.value = level
}
function openPersonalEditor(task) {
  editingPersonalTask.value = task
  newTask.value = {
    title: task.title,
    due: task.date,
    dueTime: task.time,
    note: task.note || '',
  }
  showCreate.value = true
}
async function savePersonalTask() {
  if (!newTask.value.title.trim() || !newTask.value.due) return
  const editing = editingPersonalTask.value
  const response = await apiFetch(editing ? `/api/personal-tasks/${editing.personalTaskId}/` : '/api/personal-tasks/', {
    method: editing ? 'PATCH' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: newTask.value.title,
      dueAt: `${newTask.value.due}T${newTask.value.dueTime || '23:59'}`,
      note: newTask.value.note,
    }),
  })
  if (!response.ok) {
    console.error(await response.json())
    return
  }
  const updatedTask = await response.json()
  if (editing) {
    const index = tasks.value.findIndex((task) => task.id === editing.id)
    if (index >= 0) tasks.value[index] = updatedTask
    if (selectedTask.value?.id === editing.id) selectedTask.value = updatedTask
  } else {
    tasks.value.push(updatedTask)
  }
  await loadDashboard()
  showCreate.value = false
  resetPersonalTaskForm()
}
async function deletePersonalTask() {
  const task = editingPersonalTask.value
  if (!task || !window.confirm(`确定删除“${task.title}”吗？`)) return
  const response = await apiFetch(`/api/personal-tasks/${task.personalTaskId}/`, { method: 'DELETE' })
  if (!response.ok) {
    console.error(await response.json())
    return
  }
  tasks.value = tasks.value.filter((item) => item.id !== task.id)
  await loadDashboard()
  if (selectedTask.value?.id === task.id) {
    selectedTask.value = null
    taskEditorOpen.value = false
  }
  showCreate.value = false
  resetPersonalTaskForm()
}
async function deleteSelectedPersonalTask() {
  if (!selectedTask.value || selectedTask.value.kind !== 'personal') return
  editingPersonalTask.value = selectedTask.value
  await deletePersonalTask()
}
async function loadNotifications() {
  notificationLoading.value = true
  try {
    const response = await apiFetch('/api/notifications/')
    if (!response.ok) return
    const data = await response.json()
    notifications.value = data.notifications
  } finally {
    notificationLoading.value = false
  }
}
async function openSettings() {
  showSettings.value = true
  settingsError.value = ''
  settingsMessage.value = ''
  settingsLoading.value = true
  try {
    const [settingsResponse, profileResponse] = await Promise.all([
      apiFetch('/api/notification-settings/'),
      apiFetch('/api/student-profile/'),
    ])
    if (!settingsResponse.ok) throw new Error('加载提醒设置失败')
    notificationSettings.value = await settingsResponse.json()
    if (profileResponse.ok) {
      const profile = await profileResponse.json()
      profileMotto.value = profile.motto || ''
    }
  } catch (error) {
    settingsError.value = error.message
  } finally {
    settingsLoading.value = false
  }
}
async function saveNotificationSettings() {
  settingsSaving.value = true
  settingsError.value = ''
  settingsMessage.value = ''
  try {
    const [response, profileResponse] = await Promise.all([
      apiFetch('/api/notification-settings/', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(notificationSettings.value),
      }),
      apiFetch('/api/student-profile/', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motto: profileMotto.value }),
      }),
    ])
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '保存提醒设置失败')
    if (!profileResponse.ok) throw new Error('保存个人标语失败')
    notificationSettings.value = data
    dashboard.value.identity.motto = profileMotto.value
    settingsMessage.value = data.dispatch?.sent ? `已发送 ${data.dispatch.sent} 条微信测试消息。` : '设置已保存。'
    await loadNotifications()
  } catch (error) {
    settingsError.value = error.message
  } finally {
    settingsSaving.value = false
  }
}

function connectWeChat() {
  if (!notificationSettings.value.wechatBindingAvailable) {
    settingsError.value = '微信公众号通道尚未配置完成。'
    return
  }
  window.location.assign('/api/wechat/bind/start/')
}

async function testWeChat() {
  wechatTesting.value = true
  settingsError.value = ''
  settingsMessage.value = ''
  try {
    const response = await apiFetch('/api/wechat/test/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '微信测试失败')
    settingsMessage.value = data.message
  } catch (error) {
    settingsError.value = error.message
  } finally {
    wechatTesting.value = false
  }
}

async function changePassword() {
  passwordSaving.value = true
  settingsError.value = ''
  settingsMessage.value = ''
  try {
    const response = await apiFetch('/api/auth/password/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(passwordForm.value),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '修改密码失败')
    passwordForm.value = { currentPassword: '', newPassword: '' }
    settingsMessage.value = data.message
  } catch (error) {
    settingsError.value = error.message
  } finally {
    passwordSaving.value = false
  }
}

async function markNotificationsRead(ids = null) {
  const taskIds = []
  const chatIds = []
  if (ids) {
    ids.forEach((id) => {
      const value = String(id)
      if (value.startsWith('chat-') && value.slice(5)) {
        chatIds.push(value.slice(5))
      } else if (/^\d+$/.test(value)) {
        taskIds.push(value)
      }
    })
  }
  const payload = ids
    ? { ...(taskIds.length ? { ids: taskIds } : {}), ...(chatIds.length ? { chatIds } : {}) }
    : { all: true }
  const response = await apiFetch('/api/notifications/read/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) return
  const readIds = new Set(ids || notifications.value.map((notification) => notification.id))
  notifications.value.forEach((notification) => {
    if (readIds.has(notification.id)) notification.read = true
  })
}
async function toggleNotificationPanel() {
  showNotifications.value = !showNotifications.value
  if (showNotifications.value) await loadNotifications()
}
async function openNotification(notification) {
  if (!notification.read) await markNotificationsRead([notification.id])
  const task = tasks.value.find((item) => item.id === notification.taskId)
  showNotifications.value = false
  if (notification.chatId) {
    const chat = chats.value.find((item) => item.userId === notification.chatId)
    await openChat(chat || {
      userId: notification.chatId,
      name: notification.chatName || '学习伙伴',
      initials: (notification.chatName || '学').slice(0, 1),
      unread: 0,
      lastMessage: notification.message,
      lastAt: notification.scheduledAt?.time || '刚刚',
    })
    return
  }
  if (!task) return
  activeView.value = '日历'
  selectCalendarDate(task.date, task)
  openTask(task, false)
}
async function loadBootstrap() {
  const response = await apiFetch('/api/bootstrap/')
  if (response.status === 401) {
    try {
      await loadTeacherBootstrap()
      authRole.value = 'teacher'
      return
    } catch {
      isAuthenticated.value = false
      await loadOptions()
      return
    }
  }
  if (!response.ok) throw new Error('加载学生工作台失败')
  const data = await response.json()
  isAuthenticated.value = true
  student.value = data.student
  today.value = data.today
  selectedDate.value = data.today
  calendarCursor.value = data.today
  newTask.value.due = data.today
  newTask.value.dueTime = '23:59'
  tasks.value = data.tasks
  subscriptions.value = data.subscriptions
  annualPlanYear.value = Number(data.today.slice(0, 4))
  setAnnualZoom(annualPlanZoom.value)
  await loadAnnualPlan()
  await loadDashboard()
  await loadFriends()
  await loadChats()
  await loadChatGroups()
  await nextTick()
  scrollTimelineToMinutes(timelineNowMinutes.value)
  loadNotifications().catch(console.error)
}

async function refreshStudentData() {
  if (!isAuthenticated.value || authRole.value !== 'student') return
  try {
    const response = await apiFetch('/api/bootstrap/')
    if (!response.ok) return
    const data = await response.json()
    const previousToday = today.value
    tasks.value = data.tasks
    subscriptions.value = data.subscriptions
    today.value = data.today
    if (selectedDate.value === previousToday) selectedDate.value = data.today
    if (calendarCursor.value === previousToday) calendarCursor.value = data.today
    if (newTask.value.due === previousToday) newTask.value.due = data.today
    await Promise.all([
      loadDashboard(),
      loadNotifications(),
      loadFriends(),
      loadChats(),
      loadChatGroups(),
      activeView.value === '升学规划' ? loadAnnualPlan() : Promise.resolve(),
    ])
  } catch (error) {
    console.error('后台同步失败', error)
  }
}

async function loadDashboard() {
  dashboardLoading.value = true
  dashboardError.value = ''
  try {
    const response = await apiFetch('/api/dashboard/')
    if (!response.ok) throw new Error('加载 Dashboard 数据失败')
    const data = await response.json()
    dashboard.value = data
    student.value = { ...student.value, ...data.identity }
  } catch (error) {
    dashboardError.value = error.message
  } finally {
    dashboardLoading.value = false
  }
}

async function loadOptions() {
  const response = await apiFetch('/api/options/')
  if (!response.ok) throw new Error('加载学校选项失败')
  const data = await response.json()
  schoolOptions.value = data.schools
  demoAvailable.value = Boolean(data.demo && data.teacherDemo)
  if (data.demo) demoAccount.value = data.demo
  if (data.teacherDemo) teacherDemoAccount.value = data.teacherDemo
}

function setAuthMode(mode) {
  authMode.value = mode
  authError.value = ''
  authMessage.value = ''
}

function startPasswordReset() {
  authMode.value = 'forgot'
  authError.value = ''
  authMessage.value = ''
  passwordResetForm.value.email = authRole.value === 'student'
    ? authForm.value.email
    : teacherForm.value.email
}

function returnToLogin() {
  authMode.value = 'login'
  authError.value = ''
  authMessage.value = ''
}

function setAuthRole(role) {
  authRole.value = role
  authMode.value = 'login'
  authError.value = ''
  authMessage.value = ''
}

function fillDemoAccount() {
  authForm.value.email = demoAccount.value.email
  authForm.value.password = demoAccount.value.password
  authMode.value = 'login'
}

function fillTeacherDemoAccount() {
  teacherForm.value.email = teacherDemoAccount.value.email
  teacherForm.value.password = teacherDemoAccount.value.password
  authMode.value = 'login'
}

async function submitAuth() {
  authLoading.value = true
  authError.value = ''
  authMessage.value = ''
  const isTeacher = authRole.value === 'teacher'
  const endpoint = isTeacher
    ? (authMode.value === 'login' ? '/api/auth/teacher-login/' : '/api/auth/teacher-register/')
    : (authMode.value === 'login' ? '/api/auth/login/' : '/api/auth/register/')
  const payload = isTeacher
    ? (authMode.value === 'login'
        ? { email: teacherForm.value.email, password: teacherForm.value.password }
        : teacherForm.value)
    : (authMode.value === 'login'
        ? { email: authForm.value.email, password: authForm.value.password }
        : authForm.value)
  try {
    const response = await apiFetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '操作失败，请稍后重试。')
    if (isTeacher) {
      if (authMode.value === 'register') {
        authMessage.value = data.message || '教师申请已提交，请等待管理员审核。'
        authMode.value = 'login'
      } else {
        await loadTeacherBootstrap()
      }
    } else {
      await loadBootstrap()
    }
  } catch (error) {
    authError.value = error.message
  } finally {
    authLoading.value = false
  }
}

async function submitPasswordReset() {
  authLoading.value = true
  authError.value = ''
  authMessage.value = ''
  const isConfirm = authMode.value === 'reset'
  const endpoint = isConfirm
    ? '/api/auth/password/reset/confirm/'
    : '/api/auth/password/reset/'
  const payload = isConfirm
    ? passwordResetForm.value
    : { email: passwordResetForm.value.email }
  try {
    const response = await apiFetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '密码重置失败')
    authMessage.value = data.message
    if (isConfirm) {
      window.history.replaceState({}, '', '/')
      passwordResetForm.value = { email: '', uid: '', token: '', newPassword: '' }
      authMode.value = 'login'
    }
  } catch (error) {
    authError.value = error.message
  } finally {
    authLoading.value = false
  }
}

async function logoutStudent() {
  await apiFetch('/api/auth/logout/', { method: 'POST' })
  isAuthenticated.value = false
  authRole.value = 'student'
  activeView.value = '首页'
  notifications.value = []
  showNotifications.value = false
  authForm.value = { name: '', email: '', password: '', schoolId: '', termId: '' }
  await loadOptions()
}

async function loadTeacherBootstrap() {
  const response = await apiFetch('/api/teacher/bootstrap/')
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || '教师工作台暂不可用')
  isAuthenticated.value = true
  teacher.value = data.teacher
  teacherTerms.value = data.terms
  teacherCourses.value = data.courses
  teacherClasses.value = data.classes
  teacherDeadlines.value = data.deadlines
  activeView.value = '教师工作台'
}

async function createTeacherClass() {
  teacherError.value = ''
  teacherMessage.value = ''
  const response = await apiFetch('/api/teacher/classes/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newClass.value),
  })
  const data = await response.json()
  if (!response.ok) {
    teacherError.value = data.error || '创建班级失败'
    return
  }
  teacherMessage.value = '班级已创建，现在可以发布 DDL。'
  newClass.value = { courseId: '', courseName: '', termId: '', name: '', startDate: '', endDate: '' }
  await loadTeacherBootstrap()
}

async function createTeacherDeadline() {
  teacherError.value = ''
  teacherMessage.value = ''
  const response = await apiFetch('/api/teacher/deadlines/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newDeadline.value),
  })
  const data = await response.json()
  if (!response.ok) {
    teacherError.value = data.error || '发布 DDL 失败'
    return
  }
  teacherMessage.value = 'DDL 已发布，订阅该班级的学生会自动同步。'
  newDeadline.value = { classId: '', title: '', dueAt: '', kind: 'formative', description: '' }
  await loadTeacherBootstrap()
}

function openTeacherDeadline(item) {
  editingDeadline.value = {
    id: item.id,
    title: item.title,
    description: item.description,
    kind: item.kind,
    dueAt: `${item.date}T${item.time}`,
  }
}

async function saveTeacherDeadline() {
  if (!editingDeadline.value) return
  teacherError.value = ''
  teacherMessage.value = ''
  const { id, ...payload } = editingDeadline.value
  const response = await apiFetch(`/api/teacher/deadlines/${id}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await response.json()
  if (!response.ok) {
    teacherError.value = data.error || '保存 DDL 失败'
    return
  }
  editingDeadline.value = null
  teacherMessage.value = 'DDL 已更新，学生端会同步最新内容。'
  await loadTeacherBootstrap()
}

function useExistingCourse(course) {
  newClass.value.courseId = course.id
  newClass.value.courseName = ''
  newClass.value.termId = course.termId
}

async function endTeacherCourse(course) {
  if (!window.confirm(`课程“${course.name}”结束后将不能新增订阅，确定结束吗？`)) return
  teacherError.value = ''
  teacherMessage.value = ''
  const response = await apiFetch(`/api/teacher/courses/${course.id}/end/`, { method: 'POST' })
  const data = await response.json()
  if (!response.ok) {
    teacherError.value = data.error || '结束课程失败'
    return
  }
  teacherMessage.value = '课程已结束，历史订阅和任务会保留。'
  await loadTeacherBootstrap()
}

onMounted(() => {
  const resetQuery = new URLSearchParams(window.location.search)
  const wechatStatus = resetQuery.get('wechat')
  if (wechatStatus) {
    if (wechatStatus === 'bound') settingsMessage.value = '微信绑定成功。'
    else if (wechatStatus === 'already_bound') settingsError.value = '该微信已绑定其他账号。'
    else settingsError.value = '微信绑定失败，请重新尝试。'
    window.history.replaceState({}, '', '/')
  }
  if (resetQuery.get('reset') === '1' && resetQuery.get('uid') && resetQuery.get('token')) {
    authMode.value = 'reset'
    passwordResetForm.value.uid = resetQuery.get('uid')
    passwordResetForm.value.token = resetQuery.get('token')
  }
  loadBootstrap().catch(console.error)
  document.addEventListener('keydown', handleGlobalKeydown)
  window.addEventListener('blur', cancelPointerDrag)
  window.addEventListener('blur', cancelResize)
  countdownTimer = window.setInterval(() => {
    nowTick.value = Date.now()
  }, 60000)
  syncTimer = window.setInterval(() => {
    if (document.visibilityState === 'visible') refreshStudentData()
  }, 45000)
  chatRefreshTimer = window.setInterval(() => {
    if (document.visibilityState !== 'visible' || activeView.value !== '消息') return
    loadChats()
    if (chatPeer.value && typeof chatPeer.value.userId === 'number') {
      loadChatMessages(chatPeer.value, { silent: true })
    }
  }, 12000)
  document.addEventListener('visibilitychange', refreshStudentData)
})

onUnmounted(() => {
  if (countdownTimer) window.clearInterval(countdownTimer)
  if (syncTimer) window.clearInterval(syncTimer)
  if (chatRefreshTimer) window.clearInterval(chatRefreshTimer)
  if (dashboardRefreshTimer) window.clearTimeout(dashboardRefreshTimer)
  removePointerDragListeners()
  cancelResize()
  window.clearTimeout(suppressClickTimer)
  window.removeEventListener('blur', cancelPointerDrag)
  window.removeEventListener('blur', cancelResize)
  document.removeEventListener('keydown', handleGlobalKeydown)
  document.removeEventListener('visibilitychange', refreshStudentData)
  clearChatImage()
  clearChatAttachment()
  clearChatGroupImage()
  clearChatGroupAttachment()
  clearChatGroupTask()
  cancelChatRecording()
  closeChatSocket()
  closeChatGroupSocket()
  closeChatImage()
})
</script>

<template>
  <div v-if="!isAuthenticated" class="auth-shell">
    <div class="auth-panel">
      <div class="auth-brand"><div class="brand-mark"><Check :size="19" stroke-width="3" /></div><strong>DDL<span class="brand-dot">.</span></strong></div>
      <div class="auth-heading">
        <span class="card-kicker">{{ authMode === 'forgot' || authMode === 'reset' ? '账号安全' : authRole === 'student' ? '学生学习规划' : '教师发布中心' }}</span>
        <h1>{{ authMode === 'login' ? '欢迎回来' : authMode === 'register' ? authRole === 'student' ? '创建学生账号' : '提交教师申请' : authMode === 'forgot' ? '找回密码' : '设置新密码' }}</h1>
        <p>{{ authMode === 'forgot' ? '输入注册邮箱，我们会发送一封密码重置邮件。' : authMode === 'reset' ? '设置一个新的登录密码，完成后返回登录。' : authRole === 'student' ? (authMode === 'login' ? '登录后查看你的课程 DDL 和个人安排。' : '选择学校和学期，开始建立你的学习时间表。') : (authMode === 'login' ? '审核通过后可以创建班级并发布 DDL。' : '申请提交后，需要由学校管理员在后台审核通过。') }}</p>
      </div>
      <template v-if="authMode !== 'forgot' && authMode !== 'reset'">
        <div class="auth-tabs role-tabs"><button type="button" :class="{ selected: authRole === 'student' }" @click="setAuthRole('student')">学生</button><button type="button" :class="{ selected: authRole === 'teacher' }" @click="setAuthRole('teacher')">教师</button></div>
        <div class="auth-tabs"><button type="button" :class="{ selected: authMode === 'login' }" @click="setAuthMode('login')">登录</button><button type="button" :class="{ selected: authMode === 'register' }" @click="setAuthMode('register')">注册</button></div>
      </template>
      <form class="auth-form" @submit.prevent="authMode === 'forgot' || authMode === 'reset' ? submitPasswordReset() : submitAuth()">
        <template v-if="authMode === 'forgot'">
          <label>注册邮箱<input v-model="passwordResetForm.email" required type="email" autocomplete="email" placeholder="name@example.com" /></label>
        </template>
        <template v-else-if="authMode === 'reset'">
          <input v-model="passwordResetForm.uid" type="hidden" /><input v-model="passwordResetForm.token" type="hidden" />
          <label>新密码<input v-model="passwordResetForm.newPassword" required type="password" minlength="8" autocomplete="new-password" placeholder="至少 8 位字符" /></label>
        </template>
        <template v-else-if="authRole === 'student'">
          <label v-if="authMode === 'register'">姓名<input v-model="authForm.name" required placeholder="例如：林瑞轩" /></label>
          <label>邮箱<input v-model="authForm.email" required type="email" placeholder="name@example.com" /></label>
          <label>密码<input v-model="authForm.password" required type="password" minlength="6" placeholder="至少 6 位字符" /></label>
          <template v-if="authMode === 'register'">
          <label>学校<select v-model="authForm.schoolId" required @change="authForm.termId = ''"><option value="" disabled>选择你的学校</option><option v-for="school in schoolOptions" :key="school.id" :value="school.id">{{ school.name }}</option></select></label>
          <label>当前学期<select v-model="authForm.termId" required :disabled="!selectedTerms.length"><option value="" disabled>选择当前学期</option><option v-for="term in selectedTerms" :key="term.id" :value="term.id">{{ term.name }}</option></select></label>
          </template>
        </template>
        <template v-else>
          <label v-if="authMode === 'register'">姓名<input v-model="teacherForm.name" required placeholder="例如：张老师" /></label>
          <label>邮箱<input v-model="teacherForm.email" required type="email" placeholder="teacher@example.com" /></label>
          <label>密码<input v-model="teacherForm.password" required type="password" minlength="6" placeholder="至少 6 位字符" /></label>
          <template v-if="authMode === 'register'">
            <label>学校<select v-model="teacherForm.schoolId" required><option value="" disabled>选择任教学校</option><option v-for="school in schoolOptions" :key="school.id" :value="school.id">{{ school.name }}</option></select></label>
            <label>申请说明（选填）<textarea v-model="teacherForm.proof" placeholder="例如：任教课程、工号或审核说明" /></label>
          </template>
        </template>
        <p v-if="authError" class="auth-error">{{ authError }}</p>
        <p v-if="authMessage" class="auth-message">{{ authMessage }}</p>
        <button class="primary-button full-button" type="submit" :disabled="authLoading">{{ authLoading ? '处理中...' : authMode === 'forgot' ? '发送重置邮件' : authMode === 'reset' ? '保存新密码' : authMode === 'login' ? `登录${authRole === 'student' ? '学生' : '教师'}工作台` : authRole === 'student' ? '创建并进入工作台' : '提交教师申请' }}</button>
      </form>
      <button v-if="authMode === 'login'" class="text-button auth-forgot-link" type="button" @click="startPasswordReset">忘记密码？</button>
      <button v-if="authMode === 'forgot' || authMode === 'reset'" class="text-button auth-forgot-link" type="button" @click="returnToLogin">返回登录</button>
      <template v-if="demoAvailable && authMode !== 'forgot' && authMode !== 'reset' && authRole === 'student'"><button class="demo-button" type="button" @click="fillDemoAccount">使用学生演示账号</button><p class="demo-hint">演示账号：{{ demoAccount.email }} · 密码：{{ demoAccount.password }}</p></template>
      <template v-else-if="demoAvailable && authMode !== 'forgot' && authMode !== 'reset'"><button class="demo-button" type="button" @click="fillTeacherDemoAccount">使用教师演示账号</button><p class="demo-hint">演示账号：{{ teacherDemoAccount.email }} · 密码：{{ teacherDemoAccount.password }}</p></template>
    </div>
  </div>
  <div v-else-if="authRole === 'teacher'" class="teacher-shell">
    <aside class="teacher-sidebar">
      <div class="brand"><div class="brand-mark"><Check :size="19" stroke-width="3" /></div><span>DDL<span class="brand-dot">.</span></span></div>
      <p class="teacher-school">{{ teacher.school }}</p>
      <button :class="['nav-item', { active: teacherView === '概览' }]" @click="teacherView = '概览'"><LayoutDashboard :size="18" /><span>概览</span></button>
      <button :class="['nav-item', { active: teacherView === '班级' }]" @click="teacherView = '班级'"><ListTodo :size="18" /><span>课程与班级</span></button>
      <button :class="['nav-item', { active: teacherView === '发布' }]" @click="teacherView = '发布'"><Plus :size="18" /><span>发布 DDL</span></button>
      <div class="sidebar-footer"><div class="profile"><span>{{ teacher.name.slice(0, 1) }}</span><div><strong>{{ teacher.name }}</strong><small>已审核教师</small></div><button class="logout-button" @click="logoutStudent">退出</button></div></div>
    </aside>
    <main class="teacher-main">
      <header class="topbar"><div class="breadcrumbs"><span>教师工作台</span><span>/</span><strong>{{ teacherView }}</strong></div><span class="profile-avatar">{{ teacher.name.slice(0, 1) }}</span></header>
      <div class="content-wrap teacher-content">
        <section v-if="teacherView === '概览'" class="teacher-overview">
          <div class="page-heading"><div><p class="eyebrow"><Sparkles :size="15" />教师发布中心</p><h1>你好，{{ teacher.name }}</h1><p class="subheading">你发布的 DDL 会自动同步给订阅对应班级的学生。</p></div><button class="primary-button" @click="teacherView = '发布'"><Plus :size="17" />发布 DDL</button></div>
          <div class="stats-grid"><div class="stat-card"><span>我的班级</span><strong>{{ teacherClasses.length }}</strong><small>可发布 DDL</small></div><div class="stat-card"><span>已发布 DDL</span><strong>{{ teacherDeadlines.length }}</strong><small>当前有效</small></div><div class="stat-card"><span>可加入课程</span><strong>{{ teacherCourses.length }}</strong><small>同校同学期课程</small></div></div>
          <section class="teacher-panel"><div class="panel-header"><div><h2>最近发布</h2><p>学生刷新工作台即可看到最新安排</p></div></div><div v-if="teacherDeadlines.length" class="teacher-deadline-list"><article v-for="item in teacherDeadlines" :key="item.id"><div><strong>{{ item.title }}</strong><small>{{ item.courseName }} · {{ item.className }} · {{ item.date }} {{ item.time }}</small></div><div class="deadline-actions"><span :class="['kind-tag', item.kind]">{{ item.kind === 'summative' ? 'SUM' : 'FORM' }}</span><button class="text-button" @click="openTeacherDeadline(item)">编辑</button></div></article></div><div v-else class="empty-state">还没有发布 DDL，先创建班级，再发布第一条安排。</div></section>
        </section>
        <section v-else-if="teacherView === '班级'" class="teacher-classes">
          <div class="page-heading"><div><p class="eyebrow"><ListTodo :size="15" />课程与班级</p><h1>建立班级</h1><p class="subheading">可以选择学校已有课程，或在指定学期创建新的课程。</p></div></div>
          <div class="teacher-grid"><form class="teacher-panel" @submit.prevent="createTeacherClass"><h2>新建班级</h2><label>已有课程<select v-model="newClass.courseId" @change="newClass.courseId && useExistingCourse(teacherCourses.find(course => course.id === Number(newClass.courseId)))"><option value="">新建课程</option><option v-for="course in teacherCourses" :key="course.id" :value="course.id">{{ course.name }} · {{ course.termName }}{{ course.status === 'ended' ? ' · 已结束' : '' }}</option></select></label><template v-if="!newClass.courseId"><label>学期<select v-model="newClass.termId" required><option value="" disabled>选择学期</option><option v-for="term in teacherTerms" :key="term.id" :value="term.id">{{ term.name }}</option></select></label><label>课程名称<input v-model="newClass.courseName" required placeholder="例如：AP 微积分" /></label><div class="form-two"><label>课程开始<input v-model="newClass.startDate" required type="date" /></label><label>课程结束<input v-model="newClass.endDate" required type="date" /></label></div></template><label>班级名称<input v-model="newClass.name" required placeholder="例如：A班" /></label><button class="primary-button full-button" type="submit">创建班级</button></form><section class="teacher-panel"><h2>课程生命周期</h2><div v-if="teacherCourses.length" class="teacher-course-list"><article v-for="course in teacherCourses" :key="course.id"><div><strong>{{ course.name }}</strong><small>{{ course.termName }} · {{ course.startDate || '未设置' }} 至 {{ course.endDate || '未设置' }}</small></div><div class="course-actions"><span :class="['status-tag', course.status]">{{ course.status === 'ended' ? '已结束' : course.status === 'needs_confirmation' ? '待确认结束' : '进行中' }}</span><button v-if="course.canEnd && course.status !== 'ended'" class="text-button" @click="endTeacherCourse(course)">{{ course.status === 'needs_confirmation' ? '确认结束' : '结束课程' }}</button></div></article></div><div v-else class="empty-state">还没有课程。</div></section></div>
        </section>
        <section v-else class="teacher-publish">
          <div class="page-heading"><div><p class="eyebrow"><Plus :size="15" />发布 DDL</p><h1>发布给班级</h1><p class="subheading">官方标题、说明和截止时间由教师维护，学生只能编辑自己的优先级、提醒和备注。</p></div></div>
          <form class="teacher-panel publish-form" @submit.prevent="createTeacherDeadline"><label>发布到班级<select v-model="newDeadline.classId" required><option value="" disabled>选择我的班级</option><option v-for="item in teacherClasses" :key="item.id" :value="item.id">{{ item.courseName }} · {{ item.name }}</option></select></label><div class="form-two"><label>DDL 标题<input v-model="newDeadline.title" required placeholder="例如：单元二论文提交" /></label><label>任务类型<select v-model="newDeadline.kind"><option value="formative">FORM · 形成性</option><option value="summative">SUM · 总结性</option></select></label></div><label>截止时间<input v-model="newDeadline.dueAt" required type="datetime-local" /></label><label>任务说明<textarea v-model="newDeadline.description" placeholder="说明提交内容、标准或资料链接..." /></label><p v-if="teacherError" class="auth-error">{{ teacherError }}</p><p v-if="teacherMessage" class="auth-message">{{ teacherMessage }}</p><button class="primary-button" type="submit">发布 DDL</button></form>
        </section>
        <p v-if="teacherError && teacherView !== '发布'" class="auth-error">{{ teacherError }}</p><p v-if="teacherMessage && teacherView !== '发布'" class="auth-message">{{ teacherMessage }}</p>
      </div>
    </main>
    <div v-if="editingDeadline" class="modal-backdrop" @click.self="editingDeadline = null"><form class="modal" @submit.prevent="saveTeacherDeadline"><div class="modal-header"><div><span class="eyebrow">官方 DDL</span><h2>编辑发布内容</h2></div><button type="button" class="icon-button" aria-label="关闭" @click="editingDeadline = null"><X :size="19" /></button></div><label>DDL 标题<input v-model="editingDeadline.title" required /></label><label>任务类型<select v-model="editingDeadline.kind"><option value="formative">FORM · 形成性</option><option value="summative">SUM · 总结性</option></select></label><label>截止时间<input v-model="editingDeadline.dueAt" required type="datetime-local" /></label><label>任务说明<textarea v-model="editingDeadline.description" /></label><button class="primary-button full-button" type="submit">保存并同步</button></form></div>
  </div>
  <div v-else class="app-shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark"><Check :size="19" stroke-width="3" /></div><span>DDL<span class="brand-dot">.</span></span></div>
      <nav class="main-nav">
        <button v-for="item in [{ name: '首页', icon: LayoutDashboard }, { name: '好友', icon: UsersRound }, { name: '消息', icon: MessageCircle }, { name: '我的规划', icon: ListTodo }, { name: '日历', icon: CalendarDays }, { name: '升学规划', icon: GraduationCap }, { name: '订阅中心', icon: ListTodo }]" :key="item.name" :class="['nav-item', { active: activeView === item.name }]" @click="activeView = item.name; item.name === '升学规划' && loadAnnualPlan(); item.name === '消息' && loadChats()"><component :is="item.icon" :size="18" /><span>{{ item.name }}</span><b v-if="item.name === '我的规划' && activeTasks.length">{{ activeTasks.length }}</b><b v-if="item.name === '好友' && friendRequestCount">{{ friendRequestCount }}</b><b v-if="item.name === '消息' && unreadChatCount">{{ unreadChatCount }}</b></button>
      </nav>
      <div class="sidebar-label">我的空间</div>
      <button :class="['space-button', { active: activeView === '我的空间' }]" @click="openPersonalSpace"><span>{{ student.name.slice(0, 1) }}</span>{{ student.name }}的空间<ChevronDown :size="15" /></button>
      <div class="sidebar-footer"><button class="nav-item" @click="openSettings"><Settings2 :size="18" /><span>设置</span></button><div class="profile"><span>{{ student.name.slice(0, 1) }}</span><div><strong>{{ student.name }}</strong><small>学生账号</small></div><button class="logout-button" @click="logoutStudent">退出</button></div></div>
    </aside>

    <main class="main-content">
      <header class="topbar">
        <button class="mobile-menu icon-button"><Menu :size="20" /></button>
        <div class="breadcrumbs"><span>学生工作台</span><span>/</span><strong>{{ activeView }}</strong></div>
        <div class="top-actions"><button class="icon-button" aria-label="搜索" title="搜索任务和课程" @click="openGlobalSearch"><Search :size="18" /></button><button class="icon-button notification" aria-label="打开消息" title="消息" @click="activeView = '消息'; loadChats()"><MessageCircle :size="18" /><i v-if="unreadChatCount" /></button><div class="notification-wrap"><button class="icon-button notification" aria-label="查看通知" title="通知" @click="toggleNotificationPanel"><Bell :size="18" /><i v-if="unreadNotificationCount" /></button><div v-if="showNotifications" class="notification-popover"><div class="notification-header"><div><strong>提醒通知</strong><small>{{ unreadNotificationCount ? `${unreadNotificationCount} 条未读` : '全部已读' }}</small></div><button v-if="unreadNotificationCount" class="text-button" @click="markNotificationsRead()">全部已读</button></div><div v-if="notificationLoading" class="notification-empty">正在同步提醒...</div><div v-else-if="notifications.length" class="notification-list"><button v-for="notification in notifications" :key="notification.id" :class="['notification-item', { unread: !notification.read }]" @click="openNotification(notification)"><span :class="['notification-indicator', notification.type]" /><div><strong>{{ notification.title }}</strong><p>{{ notification.message }}</p><small>{{ notification.scheduledAt.date }} {{ notification.scheduledAt.time }}</small></div></button></div><div v-else class="notification-empty">暂时没有提醒</div></div></div><span class="profile-avatar">{{ student.name.slice(0, 1) }}</span></div>
      </header>

      <div v-if="activeView === '首页'" class="content-wrap community-home-page">
        <section class="community-hero">
          <div>
            <p class="eyebrow"><UsersRound :size="15" />国际学生交流圈</p>
            <h1>今天，和同频的人一起前进</h1>
            <p class="subheading">发现同校、同课程、同申请目标的伙伴，把经验变成下一步行动。</p>
          </div>
          <button class="primary-button" @click="homeComposerOpen = true"><Plus :size="16" />分享一个想法</button>
        </section>
        <div class="community-home-tabs">
          <button v-for="tab in ['为你推荐', '我的学校', '我的课程', '华南地区']" :key="tab" :class="{ selected: homeFeedTab === tab }" @click="homeFeedTab = tab">{{ tab }}</button>
          <span class="community-online"><i /> 326 位同学正在交流</span>
        </div>
        <div class="community-home-layout">
          <main class="community-feed">
            <section class="community-composer" @click="homeComposerOpen = true">
              <span class="community-avatar">{{ student.name.slice(0, 1) }}</span>
              <button type="button">分享你的学习进展、问题或发现...</button>
              <button class="composer-plus" type="button" aria-label="创建分享"><Plus :size="16" /></button>
            </section>
            <div class="community-feed-heading"><div><h2>{{ homeFeedTab }}</h2><p>来自你可能认识的同学、老师和升学伙伴</p></div><button class="feed-filter-button" type="button"><Filter :size="14" />筛选</button></div>
            <article v-for="post in communityPosts" :key="post.id" class="community-post">
              <div class="community-post-header">
                <span class="community-avatar">{{ post.initials }}</span>
                <div class="community-post-author"><strong>{{ post.author }} <b v-if="post.verified">认证</b></strong><small>{{ post.school }} · {{ post.grade }} · {{ post.time }}</small></div>
                <button class="follow-button" :class="{ followed: post.followed }" type="button" @click="toggleHomeFollow(post)">{{ post.followed ? '已关注' : '关注' }}</button>
              </div>
              <div class="community-post-body"><span class="community-scope">{{ post.scope }}</span><h3>{{ post.title }}</h3><p>{{ post.body }}</p><div class="community-tags"><span v-for="tag in post.tags" :key="tag"># {{ tag }}</span></div></div>
              <div class="community-post-actions">
                <button :class="{ active: post.liked }" type="button" @click="toggleHomeLike(post)"><Heart :size="15" />{{ post.likes }}</button>
                <button type="button"><MessageCircle :size="15" />{{ post.comments }}</button>
                <button :class="{ active: post.saved }" type="button" @click="toggleHomeSave(post)"><Bookmark :size="15" />{{ post.saved ? '已收藏' : '收藏' }}</button>
              </div>
            </article>
          </main>
          <aside class="community-sidebar">
            <section class="community-side-section">
              <div class="community-side-heading"><div><h2>我的圈子</h2><p>你加入的小组和讨论</p></div><button type="button" aria-label="查看全部"><ChevronRight :size="15" /></button></div>
              <div class="community-group-list">
                <button v-for="group in communityGroups" :key="group.id" class="community-group" type="button" @click="toggleHomeGroup(group)">
                  <span :class="['community-group-icon', group.tone]">{{ group.icon }}</span><span class="community-group-copy"><strong>{{ group.name }}</strong><small>{{ group.meta }}</small></span><b :class="{ joined: group.joined }">{{ group.joined ? '已加入' : '加入' }}</b>
                </button>
              </div>
            </section>
            <section class="community-side-section">
              <div class="community-side-heading"><div><h2>近期活动</h2><p>别错过与你有关的机会</p></div><button type="button" aria-label="查看全部"><ChevronRight :size="15" /></button></div>
              <div class="community-event-list">
                <button v-for="event in communityEvents" :key="event.id" class="community-event" type="button" @click="toggleHomeEvent(event)">
                  <span class="community-event-date">{{ event.date }}</span><span class="community-event-copy"><strong>{{ event.title }}</strong><small><MapPin :size="11" />{{ event.place }}</small></span><b :class="{ joined: event.joined }">{{ event.joined ? '已报名' : '报名' }}</b>
                </button>
              </div>
            </section>
            <section class="community-growth-panel">
              <div class="growth-icon"><Sparkles :size="17" /></div><div><strong>本周成长记录</strong><small>完成 6 项计划，帮助了 2 位同学</small></div><ChevronRight :size="15" />
            </section>
          </aside>
        </div>
      </div>
      <div v-else-if="activeView === '好友'" class="content-wrap friends-page">
        <section class="page-heading">
          <div>
            <p class="eyebrow"><UsersRound :size="15" />学习关系</p>
            <h1>好友</h1>
            <p class="subheading">和同校、同课程、同申请阶段的同学建立更稳定的联系。</p>
          </div>
          <label class="search-box friends-search"><Search :size="16" /><input v-model="friendQuery" placeholder="搜索姓名、学校或方向..." /></label>
        </section>
        <div class="friend-stats">
          <article v-for="stat in friendStats" :key="stat.label" :class="['friend-stat', stat.tone]"><span>{{ stat.label }}</span><strong>{{ stat.value }}</strong></article>
        </div>
        <div class="friends-layout">
          <section class="friends-main">
            <div class="friend-tabs">
              <button v-for="tab in ['我的好友', '好友申请', '发现同学']" :key="tab" :class="{ selected: friendTab === tab }" @click="setFriendTab(tab)">{{ tab }}<b v-if="tab === '好友申请' && friendRequestCount">{{ friendRequestCount }}</b></button>
            </div>
            <section class="friend-panel">
              <div class="panel-header">
                <div><h2>{{ friendTab }}</h2><p>{{ friendTab === '我的好友' ? '你已经建立联系的学习伙伴' : friendTab === '好友申请' ? '处理收到的申请，也管理你发出的申请' : '从共同学校、课程和目标中发现伙伴' }}</p></div>
                <span class="space-panel-kicker">{{ filteredFriendUsers.length }} 人</span>
              </div>
              <div v-if="filteredFriendUsers.length" class="friend-list">
                <article v-for="user in filteredFriendUsers" :key="user.id" class="friend-item">
                  <button class="friend-person" type="button" @click="openFriendSpace(user)">
                    <span class="friend-avatar">{{ user.initials }}<i v-if="user.online" /></span>
                    <span class="friend-copy"><strong>{{ user.name }} <b v-if="user.verified">认证</b></strong><small>{{ user.school }} · {{ user.grade }}</small><em>{{ user.bio }}</em></span>
                  </button>
                  <span v-if="user.mutual" class="friend-mutual">{{ user.mutual }} 位共同好友</span>
                  <div class="friend-actions">
                    <button v-if="user.status === 'friend'" class="primary-button friend-action-button" type="button" @click="openChatWithUser(user)"><MessageCircle :size="14" />发消息</button>
                    <button v-if="user.status === 'friend'" class="outline-button friend-action-button" type="button" @click="removeFriend(user)">删除好友</button>
                    <template v-else-if="user.status === 'pending_received'">
                      <button class="primary-button friend-action-button" type="button" @click="acceptFriendRequest(user)">接受</button>
                      <button class="text-button friend-text-action" type="button" @click="rejectFriendRequest(user)">拒绝</button>
                    </template>
                    <button v-else-if="user.status === 'pending_sent'" class="outline-button friend-action-button" type="button" @click="cancelFriendRequest(user)">撤回申请</button>
                    <button v-else class="primary-button friend-action-button" type="button" @click="sendFriendRequest(user)"><Plus :size="14" />加好友</button>
                  </div>
                </article>
              </div>
              <div v-else class="friend-empty"><UsersRound :size="25" /><strong>{{ friendQuery ? '没有找到匹配的同学' : friendTab === '好友申请' ? '暂时没有待处理申请' : '这里还没有内容' }}</strong><small>{{ friendQuery ? '换个关键词试试。' : '先去首页认识一些同频的同学吧。' }}</small></div>
            </section>
          </section>
          <aside class="friends-aside">
            <section class="friend-panel">
              <div class="panel-header"><div><h2>关系动态</h2><p>最近的好友状态</p></div><MessageCircle :size="17" /></div>
              <div class="friend-activity-list">
                <div><span class="activity-dot green" /><p><strong>{{ friendList[0]?.name || '你的好友' }}</strong> 最近加入了申请季小组</p></div>
                <div><span class="activity-dot blue" /><p><strong>{{ incomingFriendRequests[0]?.name || '一位同学' }}</strong> 想和你成为好友</p></div>
                <div><span class="activity-dot orange" /><p>你和好友共同参与了 <strong>{{ personalJoinedEvents[0]?.title || '近期活动' }}</strong></p></div>
              </div>
            </section>
            <section class="friend-panel friend-tip">
              <Sparkles :size="18" />
              <div><strong>好友和关注有什么不同？</strong><p>关注适合接收内容更新，好友适合建立更稳定的学习联系。后续可以在好友之间发起协作。</p></div>
            </section>
          </aside>
        </div>
      </div>
      <div v-else-if="activeView === '消息'" class="content-wrap chats-page">
        <section class="page-heading chat-page-heading">
          <div>
            <p class="eyebrow"><MessageCircle :size="15" />学习伙伴</p>
            <h1>消息</h1>
            <p class="subheading">和好友聊学习、申请和下一步计划。</p>
          </div>
          <button class="outline-button" type="button" @click="activeView = '好友'"><UsersRound :size="16" />找学习伙伴</button>
        </section>
        <p v-if="chatError" class="auth-error">{{ chatError }}</p>
        <section class="chat-layout">
          <aside class="chat-sidebar">
            <div class="chat-sidebar-header">
              <div>
                <h2>会话</h2>
                <small>{{ unreadChatCount ? `${unreadChatCount} 条未读消息` : '全部消息已读' }}</small>
              </div>
              <span class="chat-count">{{ chatMode === 'private' ? filteredChats.length : filteredChatGroups.length }}</span>
            </div>
            <div class="chat-mode-tabs">
              <button type="button" :class="{ selected: chatMode === 'private' }" @click="chatMode = 'private'; chatGroup = null; closeChatGroupSocket()">私聊</button>
              <button type="button" :class="{ selected: chatMode === 'groups' }" @click="chatMode = 'groups'; chatPeer = null; closeChatSocket(); loadChatGroups()">学习小组</button>
              <button class="icon-button" type="button" aria-label="创建学习小组" title="创建学习小组" @click="chatGroupFormOpen = true"><Plus :size="15" /></button>
            </div>
            <label class="chat-search">
              <Search :size="15" />
              <input v-model="chatQuery" type="search" :placeholder="chatMode === 'private' ? '搜索好友或消息...' : '搜索小组...'" />
            </label>
            <template v-if="chatMode === 'private'">
              <div v-if="chatsLoading && !chats.length" class="chat-empty compact-empty">正在加载会话...</div>
              <div v-else-if="filteredChats.length" class="chat-list">
              <button
                v-for="chat in filteredChats"
                :key="chat.userId"
                :class="['chat-list-item', { active: chatPeer?.userId === chat.userId, unread: chat.unread }]"
                type="button"
                @click="openChat(chat)"
              >
                <span class="chat-list-avatar">{{ chat.initials || chat.name.slice(0, 1) }}<i v-if="chat.online" /></span>
                <span class="chat-list-copy">
                  <span class="chat-list-topline"><strong>{{ chat.name }}</strong><time>{{ chat.lastAt || '新会话' }}</time></span>
                  <span class="chat-list-bottomline"><small>{{ chat.lastMessage || '开始聊聊吧' }}</small><b v-if="chat.unread">{{ chat.unread > 99 ? '99+' : chat.unread }}</b></span>
                </span>
              </button>
              </div>
              <div v-else class="chat-empty">
                <MessageCircle :size="24" />
                <strong>{{ chatQuery ? '没有找到相关会话' : '还没有聊天' }}</strong>
                <small>{{ chatQuery ? '没有匹配的会话。' : '先去好友列表和同学建立联系。' }}</small>
              </div>
            </template>
            <template v-else>
              <section v-if="chatGroupInvitationCount" class="chat-group-invitation-list">
                <div class="chat-group-invitation-heading">
                  <strong>小组邀请</strong>
                  <span>{{ chatGroupInvitationCount }}</span>
                </div>
                <article v-for="invitation in chatGroupInvitations" :key="invitation.id" class="chat-group-invitation">
                  <span class="chat-list-avatar chat-group-avatar">{{ invitation.group.kind === 'course' ? '📚' : invitation.group.kind === 'event' ? '🎟️' : '✦' }}</span>
                  <div>
                    <strong>{{ invitation.group.name }}</strong>
                    <small>{{ invitation.inviter.name }} 邀请你加入</small>
                    <div class="chat-group-invitation-actions">
                      <button class="text-button" type="button" @click="respondChatGroupInvitation(invitation, 'reject')">拒绝</button>
                      <button class="primary-button" type="button" @click="respondChatGroupInvitation(invitation, 'accept')">接受</button>
                    </div>
                  </div>
                </article>
              </section>
              <div v-if="chatGroupLoading" class="chat-empty compact-empty">正在加载学习小组...</div>
              <div v-else-if="filteredChatGroups.length" class="chat-list">
                <button
                  v-for="group in filteredChatGroups"
                  :key="group.id"
                  :class="['chat-list-item', { active: chatGroup?.id === group.id }]"
                  type="button"
                  @click="openChatGroup(group)"
                >
                  <span class="chat-list-avatar chat-group-avatar">{{ group.kind === 'course' ? '📚' : group.kind === 'event' ? '🎟️' : '✦' }}</span>
                  <span class="chat-list-copy">
                    <span class="chat-list-topline"><strong>{{ group.name }}</strong><time>{{ group.lastAt || `${group.memberCount} 人` }}</time></span>
                    <span class="chat-list-bottomline"><small>{{ group.lastMessage || group.kindLabel }}</small></span>
                  </span>
                </button>
              </div>
              <div v-else class="chat-empty">
                <UsersRound :size="24" />
                <strong>{{ chatQuery ? '没有找到相关小组' : '还没有学习小组' }}</strong>
                <small>创建一个小组，和同学一起推进目标。</small>
              </div>
            </template>
          </aside>
          <section v-if="chatMode === 'private'" class="chat-main">
            <template v-if="chatPeer">
              <header class="chat-header">
                <div class="chat-header-user">
                  <span class="chat-header-avatar">{{ chatPeer.initials || chatPeer.name.slice(0, 1) }}<i v-if="chatPeer.online" /></span>
                  <div><strong>{{ chatPeer.name }}</strong><small>{{ chatPeer.online ? '在线' : `${chatPeer.school || '学习伙伴'} · ${chatPeer.grade || '学生'}` }}</small></div>
                </div>
                <div class="chat-header-actions">
                  <label v-if="chatMessageSearchOpen" class="chat-message-search">
                    <Search :size="14" />
                    <input v-model="chatMessageQuery" autofocus placeholder="搜索本次聊天" aria-label="搜索本次聊天" />
                    <button type="button" aria-label="关闭聊天搜索" title="关闭搜索" @click="toggleChatMessageSearch"><X :size="13" /></button>
                  </label>
                  <button class="icon-button" type="button" aria-label="搜索聊天记录" title="搜索聊天记录" @click="toggleChatMessageSearch"><Search :size="17" /></button>
                  <button class="icon-button" type="button" aria-label="聊天设置" title="聊天设置" @click="openFriendSpace(chatPeer)"><Settings2 :size="17" /></button>
                </div>
              </header>
              <div ref="chatMessagesRef" class="chat-messages">
                <div v-if="chatMessagesLoading" class="chat-loading">正在加载聊天记录...</div>
                <div v-else-if="!chatMessages.length" class="chat-empty chat-message-empty">
                  <MessageCircle :size="28" />
                  <strong>和 {{ chatPeer.name }} 开始对话</strong>
                  <small>可以从最近的学习安排聊起。</small>
                </div>
                <div v-else-if="!filteredChatMessages.length" class="chat-empty chat-message-empty">
                  <Search :size="28" />
                  <strong>没有找到相关消息</strong>
                  <small>试试其他关键词。</small>
                </div>
                <template v-else>
                  <div v-for="message in filteredChatMessages" :key="message.id" :class="['chat-message', { mine: message.isMine }]">
                    <span v-if="!message.isMine" class="chat-message-avatar">{{ message.senderName?.slice(0, 1) || chatPeer.name.slice(0, 1) }}</span>
                    <div class="chat-message-stack">
                      <div class="chat-bubble">
                        <img v-if="message.imageUrl" class="chat-image" :src="message.imageUrl" alt="聊天图片" title="点击查看大图" @click="openChatImage(message.imageUrl)" />
                        <audio
                          v-if="isAudioAttachment(message.attachment)"
                          class="chat-audio"
                          controls
                          preload="metadata"
                          :src="message.attachment.url"
                        />
                        <a v-else-if="message.attachment" class="chat-attachment" :href="message.attachment.url" target="_blank" rel="noopener">
                          <FileText :size="17" /><span><strong>{{ message.attachment.name }}</strong><small>{{ formatFileSize(message.attachment.size) }}</small></span><ChevronRight :size="14" />
                        </a>
                        <button v-if="message.taskCard" class="chat-task-card" type="button" @click="openSharedTaskCard(message.taskCard)">
                          <span class="chat-task-card-icon">{{ message.taskCard.source }}</span>
                          <span><strong>{{ message.taskCard.title }}</strong><small>{{ message.taskCard.date }} {{ message.taskCard.time }} · {{ message.taskCard.sourceName }}</small></span>
                          <ChevronRight :size="15" />
                        </button>
                        <span v-if="message.content">{{ message.content }}</span>
                      </div>
                      <div class="chat-message-actions">
                        <button class="icon-button" type="button" aria-label="消息操作" title="消息操作" @click.stop="toggleChatMessageActions(message)"><Ellipsis :size="15" /></button>
                        <div v-if="chatMessageActionId === message.id" class="chat-message-menu">
                          <button v-if="message.isMine && !message.recalled" type="button" @click="recallChatMessage(message)">撤回</button>
                          <button type="button" @click="deleteChatMessageLocally(message)">删除</button>
                        </div>
                      </div>
                      <time class="chat-time">{{ message.time || message.createdAt }}</time>
                    </div>
                  </div>
                </template>
              </div>
              <form
                class="chat-composer"
                :class="{ 'is-dragging': chatImageDropActive }"
                @submit.prevent="sendChatMessage"
                @dragover="handleChatDragOver"
                @dragleave="handleChatDragLeave"
                @drop="handleChatDrop"
                @paste="handleChatPaste"
              >
                <div v-if="chatImageDropActive" class="chat-drop-hint">松开即可添加图片</div>
                <div v-if="chatImagePreview" :class="['chat-image-preview', `is-${chatUploadState}`]">
                  <img :src="chatImagePreview" alt="待发送图片预览" />
                  <button type="button" class="chat-image-remove" aria-label="移除待发送图片" title="移除图片" @click="clearChatImage()"><X :size="14" /></button>
                  <small>{{ chatImageFile?.name }}</small>
                  <span v-if="chatUploadState === 'uploading'" class="chat-upload-status">图片上传 {{ chatUploadProgress }}%</span>
                  <span v-else-if="chatUploadState === 'failed'" class="chat-upload-status">发送失败，可重试</span>
                </div>
                <textarea v-model="chatDraft" rows="2" maxlength="2000" :disabled="chatSending" placeholder="输入消息，Enter 发送，Shift + Enter 换行..." @keydown="handleChatKeydown" />
                <div class="chat-composer-footer">
                  <div class="chat-composer-tools">
                    <input ref="chatImageInputRef" type="file" accept="image/jpeg,image/png,image/gif,image/webp" hidden @change="handleChatImageChange" />
                    <button class="icon-button chat-image-button" type="button" aria-label="发送图片" title="发送图片" :disabled="chatSending" @click="chatImageInputRef?.click()"><ImagePlus :size="18" /></button>
                    <input ref="chatAttachmentInputRef" type="file" accept=".pdf,.txt,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.mp3,.wav,.m4a,.webm,.ogg" hidden @change="handleChatAttachmentChange" />
                    <button class="icon-button chat-file-button" type="button" aria-label="发送文件或音频" title="发送文件或音频" :disabled="chatSending" @click="chatAttachmentInputRef?.click()"><Paperclip :size="17" /></button>
                    <button
                      v-if="!chatRecording"
                      class="icon-button chat-record-button"
                      type="button"
                      aria-label="录制语音"
                      title="录制语音"
                      :disabled="chatSending || typeof chatPeer?.userId !== 'number'"
                      @click="startChatRecording"
                    ><Mic :size="17" /></button>
                    <button
                      v-else
                      class="icon-button chat-record-button is-recording"
                      type="button"
                      aria-label="结束录音"
                      :title="`结束录音 ${recordingTimeLabel()}`"
                      @click="stopChatRecording"
                    ><Square :size="14" /></button>
                    <div class="chat-task-picker-wrap">
                      <button class="icon-button chat-task-button" type="button" aria-label="分享任务" title="分享任务" :disabled="chatSending" @click="chatTaskPickerOpen = !chatTaskPickerOpen"><ListTodo :size="17" /></button>
                      <div v-if="chatTaskPickerOpen" class="chat-task-picker">
                        <strong>分享一个任务</strong>
                        <button v-for="task in shareableChatTasks" :key="task.id" type="button" @click="selectChatTask(task)"><span>{{ task.source }}</span><span>{{ task.title }}</span><small>{{ task.date }} {{ task.time }}</small></button>
                        <small v-if="!shareableChatTasks.length">暂无可分享任务</small>
                      </div>
                    </div>
                    <small>{{ chatRecording ? `录音中 ${recordingTimeLabel()}` : `${chatDraft.length}/2000` }}</small>
                  </div>
                  <button class="primary-button" type="submit" :disabled="chatSending || (!chatDraft.trim() && !chatImageFile && !chatAttachmentFile && !chatSharedTask)"><span>{{ chatSending ? '发送中...' : chatUploadState === 'failed' ? '重试发送' : '发送' }}</span><ChevronRight :size="15" /></button>
                </div>
                <p v-if="chatRecordingError" class="chat-recording-error">{{ chatRecordingError }}</p>
                <div v-if="chatRecording" class="chat-recording-status"><span /><strong>正在录音 {{ recordingTimeLabel() }}</strong><button type="button" @click="cancelChatRecording">取消</button></div>
                <button v-if="chatAttachment" class="chat-attachment-preview" type="button" @click="clearChatAttachment">
                  <Mic v-if="isAudioAttachment(chatAttachment)" :size="16" />
                  <FileText v-else :size="16" />
                  <span>
                    <strong>{{ chatAttachment.name }}</strong>
                    <small v-if="chatUploadState === 'uploading'">上传 {{ chatUploadProgress }}%</small>
                    <small v-else-if="chatUploadState === 'failed'">发送失败，点击移除后可重新选择</small>
                    <small v-else>{{ formatFileSize(chatAttachment.size) }} · 点击移除</small>
                  </span><X :size="14" />
                </button>
                <div v-if="chatAttachment && chatUploadState === 'uploading'" class="chat-upload-progress" aria-label="文件上传进度"><i :style="{ width: `${chatUploadProgress}%` }" /></div>
                <button v-if="chatSharedTask" class="chat-shared-task-preview" type="button" @click="clearChatTask"><span>{{ chatSharedTask.source }}</span><span><strong>{{ chatSharedTask.title }}</strong><small>{{ chatSharedTask.date }} {{ chatSharedTask.time }}</small></span><X :size="14" /></button>
              </form>
            </template>
            <div v-else class="chat-empty chat-main-empty">
              <div class="chat-empty-icon"><MessageCircle :size="28" /></div>
              <strong>选择一个会话</strong>
              <small>你的学习伙伴会出现在左侧。</small>
              <button class="outline-button" type="button" @click="activeView = '好友'"><UsersRound :size="15" />去好友列表</button>
            </div>
          </section>
          <section v-else class="chat-main">
            <template v-if="chatGroup">
              <header class="chat-header">
                <div class="chat-header-user">
                  <span class="chat-header-avatar chat-group-avatar">{{ chatGroup.kind === 'course' ? '📚' : chatGroup.kind === 'event' ? '🎟️' : '✦' }}</span>
                  <div><strong>{{ chatGroup.name }}</strong><small>{{ chatGroup.kindLabel }} · {{ chatGroup.memberCount }} 位成员</small></div>
                </div>
                <div class="chat-group-header-actions">
                  <button v-if="chatGroup.joined && ['owner', 'admin'].includes(chatGroup.role)" class="outline-button chat-invite-button" type="button" @click="openChatGroupInvite"><UserPlus :size="15" />邀请好友</button>
                  <button v-if="chatGroup.role !== 'owner'" class="outline-button chat-leave-button" type="button" @click="toggleChatGroupMembership(chatGroup)">退出小组</button>
                </div>
              </header>
              <div ref="chatGroupMessagesRef" class="chat-messages">
                <div v-if="chatGroupMessagesLoading" class="chat-loading">正在加载小组消息...</div>
                <div v-else-if="!chatGroupMessages.length" class="chat-empty chat-message-empty"><UsersRound :size="28" /><strong>和小组成员开始交流</strong><small>{{ chatGroup.description || '从一个学习目标开始。' }}</small></div>
                <div v-else v-for="message in chatGroupMessages" :key="message.id" :class="['chat-message', { mine: message.isMine }]">
                  <span v-if="!message.isMine" class="chat-message-avatar">{{ message.senderName?.slice(0, 1) }}</span>
                  <div class="chat-message-stack">
                    <div class="chat-bubble">
                      <img v-if="message.imageUrl" class="chat-image" :src="message.imageUrl" alt="群聊图片" title="点击查看大图" @click="openChatImage(message.imageUrl)" />
                      <audio v-if="isAudioAttachment(message.attachment)" class="chat-audio" controls preload="metadata" :src="message.attachment.url" />
                      <a v-else-if="message.attachment" class="chat-attachment" :href="message.attachment.url" target="_blank" rel="noopener">
                        <FileText :size="17" /><span><strong>{{ message.attachment.name }}</strong><small>{{ formatFileSize(message.attachment.size) }}</small></span><ChevronRight :size="14" />
                      </a>
                      <button v-if="message.taskCard" class="chat-task-card" type="button" @click="openSharedTaskCard(message.taskCard)">
                        <span class="chat-task-card-icon">{{ message.taskCard.source }}</span>
                        <span><strong>{{ message.taskCard.title }}</strong><small>{{ message.taskCard.date }} {{ message.taskCard.time }} · {{ message.taskCard.sourceName }}</small></span>
                        <ChevronRight :size="15" />
                      </button>
                      <span v-if="message.content">{{ message.content }}</span>
                    </div>
                    <time class="chat-time">{{ message.time }}</time>
                  </div>
                </div>
              </div>
              <form v-if="chatGroup.joined" class="chat-composer" @submit.prevent="sendChatGroupMessage">
                <div v-if="chatGroupImagePreview" :class="['chat-image-preview', `is-${chatGroupUploadState}`]">
                  <img :src="chatGroupImagePreview" alt="待发送群聊图片预览" />
                  <button type="button" class="chat-image-remove" aria-label="移除待发送图片" title="移除图片" @click="clearChatGroupImage()"><X :size="14" /></button>
                  <small>{{ chatGroupImageFile?.name }}</small>
                  <span v-if="chatGroupUploadState === 'uploading'" class="chat-upload-status">图片上传 {{ chatGroupUploadProgress }}%</span>
                  <span v-else-if="chatGroupUploadState === 'failed'" class="chat-upload-status">发送失败，可重试</span>
                </div>
                <textarea v-model="chatGroupDraft" rows="2" maxlength="2000" :disabled="chatGroupSending" placeholder="和小组成员聊聊..." @keydown="handleChatGroupKeydown" />
                <div class="chat-composer-footer">
                  <div class="chat-composer-tools">
                    <input ref="chatGroupImageInputRef" type="file" accept="image/jpeg,image/png,image/gif,image/webp" hidden @change="selectChatGroupImage($event.target.files?.[0])" />
                    <button class="icon-button chat-image-button" type="button" aria-label="发送群聊图片" title="发送群聊图片" :disabled="chatGroupSending" @click="chatGroupImageInputRef?.click()"><ImagePlus :size="18" /></button>
                    <input ref="chatGroupAttachmentInputRef" type="file" accept=".pdf,.txt,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.mp3,.wav,.m4a,.webm,.ogg" hidden @change="selectChatGroupAttachment($event.target.files?.[0])" />
                    <button class="icon-button chat-file-button" type="button" aria-label="发送群聊文件或音频" title="发送群聊文件或音频" :disabled="chatGroupSending" @click="chatGroupAttachmentInputRef?.click()"><Paperclip :size="17" /></button>
                    <div class="chat-task-picker-wrap">
                      <button class="icon-button chat-task-button" type="button" aria-label="分享任务到群聊" title="分享任务到群聊" :disabled="chatGroupSending" @click="chatGroupTaskPickerOpen = !chatGroupTaskPickerOpen"><ListTodo :size="17" /></button>
                      <div v-if="chatGroupTaskPickerOpen" class="chat-task-picker">
                        <strong>分享一个任务</strong>
                        <button v-for="task in shareableChatTasks" :key="task.id" type="button" @click="selectChatGroupTask(task)"><span>{{ task.source }}</span><span>{{ task.title }}</span><small>{{ task.date }} {{ task.time }}</small></button>
                        <small v-if="!shareableChatTasks.length">暂无可分享任务</small>
                      </div>
                    </div>
                    <small>{{ chatGroupDraft.length }}/2000</small>
                  </div>
                  <button class="primary-button" type="submit" :disabled="chatGroupSending || (!chatGroupDraft.trim() && !chatGroupImageFile && !chatGroupAttachmentFile && !chatGroupSharedTask)">{{ chatGroupSending ? '发送中...' : chatGroupUploadState === 'failed' ? '重试发送' : '发送' }}<ChevronRight :size="15" /></button>
                </div>
                <button v-if="chatGroupAttachment" class="chat-attachment-preview" type="button" @click="clearChatGroupAttachment">
                  <Mic v-if="isAudioAttachment(chatGroupAttachment)" :size="16" /><FileText v-else :size="16" />
                  <span><strong>{{ chatGroupAttachment.name }}</strong><small v-if="chatGroupUploadState === 'uploading'">上传 {{ chatGroupUploadProgress }}%</small><small v-else>{{ formatFileSize(chatGroupAttachment.size) }} · 点击移除</small></span><X :size="14" />
                </button>
                <div v-if="chatGroupAttachment && chatGroupUploadState === 'uploading'" class="chat-upload-progress"><i :style="{ width: `${chatGroupUploadProgress}%` }" /></div>
                <button v-if="chatGroupSharedTask" class="chat-shared-task-preview" type="button" @click="clearChatGroupTask"><span>{{ chatGroupSharedTask.source }}</span><span><strong>{{ chatGroupSharedTask.title }}</strong><small>{{ chatGroupSharedTask.date }} {{ chatGroupSharedTask.time }}</small></span><X :size="14" /></button>
              </form>
              <div v-else class="chat-group-join"><p>加入后即可查看历史消息并参与讨论。</p><button class="primary-button" type="button" @click="toggleChatGroupMembership(chatGroup)">加入小组</button></div>
            </template>
            <div v-else class="chat-empty chat-main-empty"><div class="chat-empty-icon"><UsersRound :size="28" /></div><strong>选择一个学习小组</strong><small>和跨校同学一起完成目标。</small></div>
          </section>
        </section>
      </div>
      <div v-else-if="activeView === '我的规划'" class="content-wrap dashboard-page">
        <section :class="['dashboard-cockpit', `is-${dashboardTodayState}`]">
          <div class="cockpit-topline">
            <span class="cockpit-kicker"><Sparkles :size="14" />我的规划 / 今日状态</span>
            <button class="cockpit-date" type="button" @click="scrollToDashboardToday"><CalendarDays :size="14" />{{ todayLabel }}</button>
          </div>
          <div class="cockpit-grid">
            <div
              class="cockpit-student"
              role="button"
              tabindex="0"
              :aria-expanded="dashboardIdentityExpanded"
              @click="dashboardIdentityExpanded = !dashboardIdentityExpanded"
              @keydown.enter.prevent="dashboardIdentityExpanded = !dashboardIdentityExpanded"
            >
              <div class="cockpit-avatar" aria-hidden="true">
                <div class="cockpit-avatar-ring" />
                <div class="cockpit-avatar-head"><UserRound :size="27" /></div>
                <div class="cockpit-avatar-body"><GraduationCap :size="25" /></div>
                <span>{{ dashboard.identity.grade || '学生' }}</span>
              </div>
              <div class="cockpit-student-copy">
                <small>我的身份</small>
                <strong>{{ student.name || '同学' }}</strong>
                <span>{{ dashboard.identity.grade || '学生' }} · {{ dashboard.identity.curriculum || '学习规划' }}</span>
              </div>
              <ChevronDown :class="{ rotated: dashboardIdentityExpanded }" :size="17" />
            </div>
            <div class="cockpit-main-copy">
              <span class="cockpit-status-label">{{ dashboardStateCopy.label }}</span>
              <h1>{{ dashboard.identity.greeting || '你好' }}，{{ student.name || '同学' }}</h1>
              <p>{{ dashboardStateCopy.title }}</p>
              <small>{{ dashboard.identity.motto || dashboardStateCopy.description }}</small>
            </div>
            <div
              class="cockpit-metric cockpit-progress-metric"
              role="button"
              tabindex="0"
              :aria-expanded="dashboardProgressExpanded"
              @click="dashboardProgressExpanded = !dashboardProgressExpanded"
              @keydown.enter.prevent="dashboardProgressExpanded = !dashboardProgressExpanded"
            >
              <div class="cockpit-metric-head"><span>今日完成率</span><ChevronDown :class="{ rotated: dashboardProgressExpanded }" :size="16" /></div>
              <div class="cockpit-progress-value"><strong>{{ dashboardCompletionPercent }}%</strong><span>{{ dashboardCompletedCount }}/{{ dashboardTodayTasks.length || 0 }} 项</span></div>
              <div class="cockpit-progress-bar"><i :style="{ width: `${dashboardCompletionPercent}%` }" /></div>
              <small>点击查看任务构成</small>
            </div>
            <div
              class="cockpit-metric cockpit-streak-metric"
              role="button"
              tabindex="0"
              :aria-expanded="dashboardCheckinExpanded"
              @click="dashboardCheckinExpanded = !dashboardCheckinExpanded"
              @keydown.enter.prevent="dashboardCheckinExpanded = !dashboardCheckinExpanded"
            >
              <div class="cockpit-metric-head"><span>连续打卡</span><ChevronDown :class="{ rotated: dashboardCheckinExpanded }" :size="16" /></div>
              <div class="cockpit-streak-value"><strong>{{ dashboard.checkin.streak || 0 }}</strong><span>天</span></div>
              <small>{{ dashboard.checkin.checkedIn ? '今天已记录' : '完成全部任务后记录' }}</small>
            </div>
          </div>
          <div v-if="dashboardIdentityExpanded" class="cockpit-expand cockpit-identity-expand">
            <div><span>学校</span><strong>{{ dashboard.identity.school || student.school || '待补充' }}</strong></div>
            <div><span>年级</span><strong>{{ dashboard.identity.grade || '学生' }}</strong></div>
            <div><span>课程体系</span><strong>{{ dashboard.identity.curriculum || '待补充' }}</strong></div>
            <div><span>当前学期</span><strong>{{ dashboard.identity.term || student.term || '待补充' }}</strong></div>
          </div>
          <div v-if="dashboardProgressExpanded" class="cockpit-expand cockpit-breakdown-expand">
            <div v-for="item in dashboardTaskBreakdown" :key="item.label" :class="['cockpit-breakdown-item', item.tone]">
              <span>{{ item.label }}</span><strong>{{ item.value }}</strong>
            </div>
          </div>
          <div v-if="dashboardCheckinExpanded" class="cockpit-expand cockpit-checkin-expand">
            <div class="cockpit-checkin-title"><span>最近 7 天</span><small>每天最多记录一次</small></div>
            <div class="cockpit-checkin-days">
              <div v-for="item in dashboardRecentCheckins" :key="item.date" :class="{ today: item.date === today, checked: item.checkedIn }">
                <span>{{ dashboardCheckinLabel(item) }}</span><i :title="item.checkedIn ? `${item.percent}% 完成` : '未打卡'" /><small>{{ item.checkedIn ? '已完成' : '—' }}</small>
              </div>
            </div>
          </div>
          <div class="cockpit-footer">
            <span><Clock3 :size="14" />{{ dashboardStateCopy.description }}</span>
            <button type="button" @click="scrollToDashboardToday">查看今日任务 <ChevronRight :size="15" /></button>
          </div>
        </section>
        <div v-if="dashboardLoading" class="dashboard-syncing"><Clock3 :size="13" />正在同步最新任务</div>
        <p v-if="dashboardError" class="dashboard-error">{{ dashboardError }}</p>
        <section ref="dashboardTodayGridRef" class="dashboard-today-grid">
          <section class="today-panel dashboard-panel">
            <div class="panel-header">
              <div><h2>今日 DDL / Event</h2><p>老师、顾问和订阅内容会自动同步</p></div>
              <span class="date-pill">{{ dashboardOfficialTodayTasks.length }} 项</span>
            </div>
            <div class="task-list timeline-list dashboard-list">
              <article v-for="task in dashboardOfficialTodayTasks" :key="task.id" :class="['list-task', task.level, { completed: task.done, dragging: draggingTask?.id === task.id }]" data-pointer-draggable="true" @pointerdown="beginPointerDrag(task, $event)" @click="openTaskFromPointer(task)">
                <span class="list-task-time">{{ task.time }}</span><span class="source-icon">{{ task.source }}</span><div><strong>{{ task.title }}</strong><small>{{ task.sourceName }} · {{ task.publisher }}</small></div><span class="list-status">{{ task.done ? '已完成' : task.status === 'doing' ? '进行中' : task.level === 'urgent' ? '紧急' : '待处理' }}</span><button class="check-button" @click.stop="toggleTask(task)"><Check v-if="task.done" :size="13" /></button>
              </article>
              <div v-if="!dashboardOfficialTodayTasks.length" class="empty-state">今天没有官方安排，给自己留一点空间。</div>
            </div>
          </section>
          <section ref="todoPanelRef" class="today-panel dashboard-panel todo-panel" :class="{ 'drop-ready': dragOverZone === 'todo' }" @dragover="handleTodoDragOver" @dragleave="clearDragOver" @drop.prevent="dropOnTodo">
            <div class="panel-header"><div><h2>个人 ToDo</h2><p>只属于你的今日计划</p></div><button class="text-button" @click="resetPersonalTaskForm(); showCreate = true"><Plus :size="14" />添加</button></div>
            <div v-if="draggingTask" :class="['todo-drop-hint', { over: dragOverZone === 'todo', blocked: draggingTask.kind !== 'personal' }]">{{ draggingTask.kind === 'personal' ? '松开鼠标，从时间轴移出这个个人任务' : '官方 DDL 不支持移出时间轴' }}</div>
            <div class="task-list dashboard-list">
              <article v-for="task in dashboardPersonalTodayTasks" :key="task.id" :class="['todo-task', { completed: task.done, scheduled: task.plannedStart, dragging: draggingTask?.id === task.id }]" data-pointer-draggable="true" @pointerdown="beginPointerDrag(task, $event)" @click="openTaskFromPointer(task)">
                <button class="check-button" @click.stop="toggleTask(task)"><Check v-if="task.done" :size="13" /></button><div><strong>{{ task.title }}</strong><small>{{ task.plannedStart ? `已安排 ${task.plannedStart.time} · ` : '' }}{{ task.done ? '已完成' : task.status === 'doing' ? '进行中' : task.priority === 'high' ? '高优先级' : '个人安排' }}</small></div><button class="inline-edit" @click.stop="openPersonalEditor(task)">编辑</button>
              </article>
              <div v-if="!dashboardPersonalTodayTasks.length" class="empty-state">给今天定一个小目标吧。</div>
            </div>
            <button class="todo-add-row" @click="resetPersonalTaskForm(); showCreate = true"><Plus :size="15" />添加新的 ToDo</button>
          </section>
        </section>
        <section class="dashboard-timeline-panel">
          <div class="panel-header">
            <div><h2>今日时间轴</h2><p>安排今天的官方 DDL 和个人 ToDo，重叠任务会自动横向并列</p></div>
            <div class="today-panel-actions">
              <div class="view-switch compact" aria-label="今日时间轴视图">
                <button type="button" :class="{ selected: timelineView === '列表' }" @click="timelineView = '列表'">列表</button>
                <button type="button" :class="{ selected: timelineView === '时间轴' }" @click="timelineView = '时间轴'">时间轴</button>
              </div>
              <span class="date-pill">{{ dashboardTimelineTasks.length }} 项已排入</span>
            </div>
          </div>
          <template v-if="timelineView === '列表'">
            <div class="timeline-list dashboard-list standalone-timeline-list">
              <article v-for="task in dashboardTimelineTasks" :key="task.id" :class="['list-task', task.level, { completed: task.done, dragging: draggingTask?.id === task.id }]" data-pointer-draggable="true" @pointerdown="beginPointerDrag(task, $event)" @click="openTaskFromPointer(task)">
                <span class="list-task-time">{{ task.plannedStart ? task.plannedStart.time : task.time }}</span><span class="source-icon">{{ task.source }}</span><div><strong>{{ task.title }}</strong><small>{{ hasTimelineDuration(task) ? `${task.plannedStart.time} - ${task.plannedEnd.time} · ` : '' }}{{ task.sourceName }} · {{ task.kind === 'personal' ? '个人任务' : task.publisher }}</small></div><span class="list-status">{{ task.done ? '已完成' : task.status === 'doing' ? '进行中' : '待处理' }}</span><button class="check-button" @click.stop="toggleTask(task)"><Check v-if="task.done" :size="13" /></button>
              </article>
              <div v-if="!dashboardTimelineTasks.length" class="empty-state">今天还没有排入任务。</div>
            </div>
          </template>
          <template v-else>
            <div class="timeline-view">
              <div class="timeline-overview">
                <div class="timeline-overview-heading"><strong>全天概览</strong><small>点击色点或色条，跳到对应时间</small></div>
                <button class="timeline-overview-track" type="button" aria-label="全天时间概览" :style="{ height: `${timelineOverviewHeight}px` }" @click="scrollTimelineFromOverview">
                  <span v-for="mark in [0, 6, 12, 18, 24]" :key="mark" class="timeline-overview-label" :style="{ left: `${(mark / 24) * 100}%` }">{{ String(mark).padStart(2, '0') }}:00</span>
                  <i v-for="task in dashboardTimelineTasks" :key="`overview-${task.id}`" :class="['timeline-overview-task', task.level, { duration: timelineIsDuration(task), point: !timelineIsDuration(task) }]" :style="{ top: `${16 + task.lane * 12}px`, left: `${(timelineStartMinutes(task) / 1440) * 100}%`, width: timelineIsDuration(task) ? `${Math.max(1.4, (timelineTaskDuration(task) / 1440) * 100)}%` : '8px' }" :title="`${task.title} · ${minutesToTime(timelineStartMinutes(task))}`" @click.stop="scrollTimelineToMinutes(timelineStartMinutes(task))" />
                </button>
              </div>
              <button class="timeline-now-button" type="button" @click="scrollTimelineToMinutes(timelineNowMinutes)"><Clock3 :size="13" />跳到现在</button>
              <div ref="timelineBoardRef" class="timeline-board vertical-timeline-board" :class="{ 'drop-ready': dragOverZone === 'timeline' }" :style="{ height: `${Math.min(650, timelineCanvasHeight)}px` }" @dragover="handleTimelineDragOver" @dragleave="clearDragOver" @drop.prevent="dropOnTimeline">
                <div class="timeline-canvas" :style="{ height: `${timelineCanvasHeight}px` }">
                  <div class="timeline-grid" aria-hidden="true" />
                  <div class="timeline-hour-labels" aria-hidden="true">
                    <span v-for="mark in timelineHourMarks" :key="mark.hour" :class="{ major: mark.hour % 2 === 0 }" :style="{ top: `${timelineHeaderHeight + mark.hour * timelineHourHeight}px` }">{{ mark.label }}</span>
                  </div>
                  <div class="timeline-task-layer">
                    <div v-if="timelineNowPosition !== null" class="timeline-now" :style="{ top: `${timelineNowPosition}px` }"><span>现在</span></div>
                    <div v-if="timelineDragMinutes !== null && draggingTask" class="timeline-drop-preview" :style="{ top: `${timelineHeaderHeight + (timelineDragMinutes / 60) * timelineHourHeight}px` }"><span>{{ timelineDragLabel }}</span></div>
                    <article v-for="task in dashboardTimelineTasks" :key="task.id" :class="['axis-task', task.level, { completed: task.done, duration: timelineIsDuration(task), point: !timelineIsDuration(task), dragging: draggingTask?.id === task.id, resizing: resizeDraft?.id === task.id }]" :style="timelineTaskStyle(task)" data-pointer-draggable="true" role="button" tabindex="0" :title="`${task.title} · ${timelineTaskTimeLabel(task)}`" @pointerdown="beginPointerDrag(task, $event)" @click="openTaskFromPointer(task)" @keydown.enter="openTask(task)">
                      <template v-if="!timelineIsDuration(task)"><span class="axis-point-dot" aria-hidden="true" /><span class="axis-point-label"><span class="axis-task-time">{{ timelineTaskTimeLabel(task) }}</span><strong>{{ task.title }}</strong><small>{{ task.source }} {{ task.sourceName }}</small></span></template><template v-else><span class="axis-task-time">{{ timelineTaskTimeLabel(task) }}</span><strong>{{ task.title }}</strong><small>{{ task.source }} {{ task.sourceName }}</small><span class="axis-task-duration">{{ timelineTaskDuration(task) }} 分钟</span><button v-if="hasTimelineDuration(task) && resizeDraft?.id !== task.id" class="axis-point-toggle" aria-label="还原为时间节点" title="还原为时间节点" @click.stop="restoreTaskToPoint(task)"><CircleDot :size="12" /></button></template><button class="check-button" :aria-label="task.done ? '标记为未完成' : '标记为完成'" @click.stop="toggleTask(task)"><Check v-if="task.done" :size="11" /></button><span class="axis-resize-handle" aria-label="调整计划时长" @pointerdown.stop.prevent="startResize(task, $event)" @click.stop.prevent />
                    </article>
                  </div>
                  <div v-if="!dashboardTimelineTasks.length" class="timeline-board-empty">从右侧个人 ToDo 列表拖一个任务到时间轴上</div>
                </div>
              </div>
              <p v-if="timelineError" class="timeline-error">{{ timelineError }}</p>
              <div class="drop-zones">
                <div ref="urgentDropZoneRef" :class="['drop-zone', { over: dragOverZone === 'urgent' }]" @dragover.prevent="dragOverZone = 'urgent'" @dragleave="clearDragOver" @drop.prevent="dropToZone('urgent')"><span>⚡</span><div><strong>提高优先级</strong><small>将任务标记为高优先级</small></div></div>
                <div ref="completedDropZoneRef" :class="['drop-zone', 'completed-zone', { over: dragOverZone === 'completed' }]" @dragover.prevent="dragOverZone = 'completed'" @dragleave="clearDragOver" @drop.prevent="dropToZone('completed')"><span>✓</span><div><strong>已完成</strong><small>完成的任务会保留并划掉</small></div></div>
              </div>
            </div>
          </template>
        </section>
        <section class="week-panel dashboard-week-panel">
          <div class="panel-header"><div><h2>本周任务</h2><p>{{ dashboard.week.start ? `${dashboard.week.start.slice(5).replace('-', '月')}日 - ${dashboard.week.end.slice(5).replace('-', '月')}日` : '提前看见本周的忙碌程度' }}</p></div><span class="week-total">{{ dashboardWeekTasks.length }} 个 DDL</span></div>
          <div class="dashboard-week-list">
            <div v-for="(task, index) in dashboardVisibleWeekTasks" :key="task.id" :class="['dashboard-week-item', task.level, { completed: task.done }]" @click="openTask(task)">
              <span class="week-rank">{{ index + 1 }}</span><div class="week-task-main"><strong>{{ task.title }}</strong><small>{{ task.sourceName }} · {{ task.publisher }}</small></div><strong v-if="task.id === dashboardFocusWeekTask?.id" class="week-countdown">{{ countdownLabel(task) }}</strong><span v-else class="week-date">{{ task.date.slice(5).replace('-', '月') }}日</span>
            </div>
            <div v-if="!dashboardWeekTasks.length" class="empty-state">本周没有官方 DDL，享受轻松的一周吧。</div>
          </div>
          <button v-if="dashboardHiddenWeekCount" class="week-more-button" @click="showAllWeekTasks = !showAllWeekTasks">{{ showAllWeekTasks ? '收起' : `+${dashboardHiddenWeekCount} 更多` }}</button>
          <button class="text-button" @click="activeView = '日历'">查看完整日历 <ChevronRight :size="15" /></button>
        </section>
        <nav class="dashboard-quick-links" aria-label="快捷入口">
          <button @click="activeView = '日历'"><CalendarDays :size="18" /><span>完整日历</span><ChevronRight :size="14" /></button>
          <button @click="activeView = '订阅中心'"><ListTodo :size="18" /><span>订阅中心</span><ChevronRight :size="14" /></button>
          <button class="disabled-link" disabled><Trophy :size="18" /><span>成就墙</span><small>即将开放</small></button>
          <button @click="openSettings"><Settings2 :size="18" /><span>设置</span><ChevronRight :size="14" /></button>
        </nav>
      </div>

      <div v-else-if="activeView === '日历'" class="content-wrap calendar-page">
        <section class="page-heading">
          <div><p class="eyebrow"><CalendarDays :size="15" />全盘掌控</p><h1>日历</h1><p class="subheading">把课程、升学和个人安排放在同一张时间表里。</p></div>
          <button class="primary-button" @click="openPersonalTaskCreate(selectedDate)"><Plus :size="17" />创建个人待办</button>
        </section>
        <div class="calendar-layout">
          <section class="big-calendar">
            <div class="calendar-toolbar">
              <div class="view-switch"><button v-for="mode in ['月','周','日']" :key="mode" :class="{ selected: calendarMode === mode }" @click="setCalendarMode(mode)">{{ mode }}</button></div>
              <button class="today-button" @click="goToToday">返回今天</button>
              <div class="month-controls"><button aria-label="上一段时间" @click="shiftCalendar(-1)"><ChevronLeft :size="15" /></button><strong>{{ calendarPeriodLabel }}</strong><button aria-label="下一段时间" @click="shiftCalendar(1)"><ChevronRight :size="15" /></button></div>
            </div>

            <template v-if="calendarMode === '月'">
              <div class="calendar-weekdays"><span v-for="day in ['一','二','三','四','五','六','日']" :key="day">{{ day }}</span></div>
              <div class="calendar-grid big"><button v-for="day in calendarMonthDays" :key="day.iso" :class="['calendar-day', { outside: day.outside, selected: day.iso === selectedDate, today: day.iso === today }]" @click="selectCalendarDate(day.iso)" @dblclick="openDayView(day.iso)"><strong>{{ day.number }}</strong><div class="calendar-events"><span v-for="task in day.tasks.slice(0, 3)" :key="task.id" :class="task.level" @click.stop="selectCalendarDate(day.iso, task)">{{ task.title.slice(0, 9) }}</span><small v-if="day.tasks.length > 3">还有 {{ day.tasks.length - 3 }} 项</small></div></button></div>
            </template>

            <template v-else-if="calendarMode === '周'">
              <div class="week-calendar">
                <button v-for="day in calendarWeekDays" :key="day.iso" :class="['week-day-column', { selected: day.iso === selectedDate, today: day.isToday }]" @click="selectCalendarDate(day.iso)" @dblclick="openDayView(day.iso)">
                  <div class="week-day-heading"><small>{{ day.weekday }}</small><strong>{{ day.number }}</strong></div>
                  <div class="week-day-events"><span v-for="task in day.tasks" :key="task.id" :class="task.level" @click.stop="selectCalendarDate(day.iso, task)"><b>{{ task.time }}</b>{{ task.title }}</span><p v-if="!day.tasks.length">无安排</p></div>
                </button>
              </div>
            </template>

            <template v-else>
              <div class="day-calendar">
                <div class="day-calendar-heading"><strong>{{ calendarPeriodLabel }}</strong><span>{{ calendarSelectedTasks.length }} 项安排</span></div>
                <div class="day-hours"><div v-for="hour in dayHours" :key="hour" class="day-hour-row"><time>{{ hour }}:00</time><div><button v-for="task in tasksAtHour(hour)" :key="task.id" :class="['day-task', task.level, { completed: task.done }]" @click="selectCalendarDate(selectedDate, task)"><b>{{ task.time }}</b><span>{{ task.title }}</span><small>{{ task.sourceName }}</small></button></div></div></div>
              </div>
            </template>
          </section>
          <aside class="focus-drawer">
            <div class="drawer-header"><div><span class="card-kicker">{{ selectedDate === today ? '今日聚焦' : '选中日期' }}</span><h2>{{ selectedTask ? '任务详情' : `${selectedDate.slice(5).replace('-', '月')}日的安排` }}</h2></div><Filter :size="17" /></div>
            <div v-if="selectedTask" class="detail"><span class="detail-source">{{ selectedTask.source }} {{ selectedTask.sourceName }}</span><h3>{{ selectedTask.title }}</h3><div class="detail-time"><Clock3 :size="17" /><strong>{{ remainingTime }}</strong></div><p>{{ selectedTask.description }}</p><small v-if="selectedTask.kind !== 'personal'">发布者：{{ selectedTask.publisher }}</small><button class="primary-button full-button" @click="toggleTask(selectedTask)">{{ selectedTask.done ? '标记为未完成' : '标记为已完成' }}</button><div v-if="selectedTask.kind === 'personal'" class="calendar-personal-task-actions"><button class="outline-button" @click="openPersonalEditor(selectedTask)"><Pencil :size="14" />编辑待办</button><button class="danger-button" @click="deleteSelectedPersonalTask">删除待办</button></div><button class="back-button" @click="selectedTask = null">返回当天清单</button></div>
            <div v-else class="drawer-list"><div v-for="task in calendarSelectedTasks" :key="task.id" class="drawer-task" @click="selectCalendarDate(selectedDate, task)"><span :class="['mini-dot', task.level]" /><div><strong>{{ task.time }} · {{ task.title }}</strong><small>{{ task.sourceName }}</small></div></div><div v-if="!calendarSelectedTasks.length" class="empty-state">暂无安排</div></div>
          </aside>
        </div>
      </div>

      <div v-else-if="activeView === '订阅中心'" class="content-wrap subscription-page"><section class="page-heading"><div><p class="eyebrow"><ListTodo :size="15" />应用商店式选课</p><h1>订阅中心</h1><p class="subheading">选择你正在上的班级，DDL 会自动出现在你的日历里。</p></div><label class="search-box"><Search :size="16" /><input v-model="query" placeholder="搜索课程或发布者..." /></label></section><div class="subscription-tabs"><button v-for="tab in ['我的课程','升学','全部']" :key="tab" :class="{ selected: filter === tab }" @click="filter = tab">{{ tab === '我的课程' ? '📚 我的课程' : tab === '升学' ? '🎓 升学顾问推荐' : '✨ 全部订阅' }}</button></div><p v-if="subscriptionError" class="auth-error">{{ subscriptionError }}</p><div v-if="!filteredSubscriptions.length" class="subscription-empty"><span>{{ filter === '升学' ? '🎓' : '📚' }}</span><strong>{{ filter === '我的课程' ? '还没有订阅课程' : filter === '升学' ? '升学内容即将开放' : '没有找到匹配内容' }}</strong><small>{{ filter === '我的课程' ? '去“全部订阅”选择你正在上的班级。' : filter === '升学' ? '后续可以订阅升学顾问发布的申请节点。' : '换个关键词试试看。' }}</small></div><div v-else class="subscription-grid"><article v-for="item in filteredSubscriptions" :key="item.id" class="subscription-card"><div :class="['subscription-icon', item.color]">{{ item.type === '课程' ? '📚' : item.type === '升学' ? '🎓' : '✨' }}</div><div class="subscription-body"><span>{{ item.type }}</span><h2>{{ item.name }}</h2><p>{{ item.publisher }}</p><small>本学期 {{ item.count }} 个 DDL</small><em v-if="item.courseSubscribed && !item.subscribed" class="course-lock-label">已订阅：{{ item.currentClassName || '其他班级' }}</em><em v-else-if="item.courseStatus === 'ended'" class="ended-label">课程已结束</em><em v-else-if="item.courseStatus === 'needs_confirmation'" class="ended-label pending">待教师确认结束</em></div><button :class="['subscribe-button', { subscribed: item.subscribed }]" :disabled="!item.subscribed && (item.courseStatus === 'ended' || item.courseSubscribed)" @click="toggleSubscription(item)">{{ item.subscribed ? '✓ 已订阅' : item.courseSubscribed ? '已订阅其他班级' : item.courseStatus === 'ended' ? '已结束' : '+ 订阅' }}</button></article></div><div class="subscription-summary">已订阅 <strong>{{ subscriptions.filter(item => item.subscribed).length }}</strong> 门内容，共 <strong>{{ subscriptions.filter(item => item.subscribed).reduce((sum, item) => sum + item.count, 0) }}</strong> 个待办事项</div></div>
      <div v-else-if="activeView === '我的空间'" class="content-wrap space-page">
        <section class="page-heading">
          <div>
            <p class="eyebrow"><UserRound :size="15" />个人空间</p>
            <h1>{{ student.name }} 的空间</h1>
            <p class="subheading">这里放你的身份、收藏、成长记录和可见范围。</p>
          </div>
          <div class="space-heading-actions">
            <button class="outline-button" @click="openSettings"><Settings2 :size="16" />编辑资料</button>
            <button class="primary-button" @click="togglePersonalPrivacy"><Sparkles :size="16" />{{ personalSpaceVisibility }}</button>
          </div>
        </section>
        <section class="space-hero">
          <div class="space-profile-card">
            <div class="space-avatar">{{ student.name.slice(0, 1) }}</div>
            <div class="space-profile-copy">
              <span class="space-privacy-pill">{{ personalSpaceVisibility }}</span>
              <h2>{{ student.name }}</h2>
              <p>{{ dashboard.identity.school || student.school || '学校信息待补充' }} · {{ dashboard.identity.grade || '学生' }} · {{ dashboard.identity.curriculum || '学习规划' }}</p>
              <small>{{ profileMotto || dashboard.identity.motto || '把计划做好，也把自己展示好。' }}</small>
            </div>
          </div>
          <div class="space-stats">
            <article v-for="stat in personalSpaceStats" :key="stat.label" :class="['space-stat-card', stat.tone]">
              <span>{{ stat.label }}</span><strong>{{ stat.value }}</strong>
            </article>
          </div>
        </section>
        <div class="space-layout">
          <section class="space-main">
            <div class="space-tabs">
              <button v-for="tab in ['动态', '收藏', '成长', '隐私']" :key="tab" :class="{ selected: personalSpaceTab === tab }" @click="setPersonalSpaceTab(tab)">{{ tab }}</button>
            </div>
            <div v-if="personalSpaceTab === '动态'" class="space-panel">
              <div class="panel-header">
                <div><h2>我的动态</h2><p>你在社区里的发言和参与</p></div>
                <button class="text-button" @click="homeComposerOpen = true">去发帖 <ChevronRight :size="15" /></button>
              </div>
              <div v-if="personalMyPosts.length" class="space-feed">
                <article v-for="post in personalMyPosts.slice(0, 4)" :key="post.id" class="space-post">
                  <div class="community-post-header">
                    <span class="community-avatar">{{ post.initials }}</span>
                    <div class="community-post-author"><strong>{{ post.author }}</strong><small>{{ post.school }} · {{ post.grade }} · {{ post.time }}</small></div>
                    <button class="follow-button followed" type="button">本人</button>
                  </div>
                  <div class="community-post-body"><span class="community-scope">{{ post.scope }}</span><h3>{{ post.title }}</h3><p>{{ post.body }}</p><div class="community-tags"><span v-for="tag in post.tags" :key="tag"># {{ tag }}</span></div></div>
                </article>
              </div>
              <div v-else class="empty-state">还没有自己的发帖，去首页分享一个学习进展吧。</div>
              <div class="space-mini-grid">
                <article class="space-mini-card">
                  <strong>最近参与</strong>
                  <small>{{ personalJoinedEvents.length ? personalJoinedEvents[0].title : '暂时没有报名活动' }}</small>
                </article>
                <article class="space-mini-card">
                  <strong>收藏速览</strong>
                  <small>{{ personalSavedPosts.length ? `${personalSavedPosts.length} 条收藏` : '还没有收藏内容' }}</small>
                </article>
              </div>
            </div>
            <div v-else-if="personalSpaceTab === '收藏'" class="space-panel">
              <div class="panel-header">
                <div><h2>我的收藏</h2><p>你保存下来反复看的内容</p></div>
                <span class="space-panel-kicker">{{ personalSavedPosts.length }} 条</span>
              </div>
              <div v-if="personalSavedPosts.length" class="space-feed">
                <article v-for="post in personalSavedPosts" :key="post.id" class="space-post">
                  <div class="community-post-header">
                    <span class="community-avatar">{{ post.initials }}</span>
                    <div class="community-post-author"><strong>{{ post.author }}</strong><small>{{ post.school }} · {{ post.grade }} · {{ post.time }}</small></div>
                  </div>
                  <div class="community-post-body"><span class="community-scope">{{ post.scope }}</span><h3>{{ post.title }}</h3><p>{{ post.body }}</p></div>
                </article>
              </div>
              <div v-else class="empty-state">还没有收藏内容，看到有用的经验就先存下来。</div>
            </div>
            <div v-else-if="personalSpaceTab === '成长'" class="space-panel">
              <div class="panel-header">
                <div><h2>成长记录</h2><p>把你的行动痕迹变成可见的积累</p></div>
              </div>
              <div class="space-badge-grid">
                <article v-for="badge in personalBadges" :key="badge.title" :class="['badge-card', { active: badge.active }]">
                  <span>{{ badge.active ? '✓' : '·' }}</span>
                  <div><strong>{{ badge.title }}</strong><small>{{ badge.desc }}</small></div>
                </article>
              </div>
              <div class="space-mini-grid">
                <article class="space-mini-card">
                  <strong>已加入小组</strong>
                  <small>{{ personalJoinedGroups.length ? personalJoinedGroups.map((group) => group.name).join(' / ') : '暂时没有加入小组' }}</small>
                </article>
                <article class="space-mini-card">
                  <strong>参与活动</strong>
                  <small>{{ personalJoinedEvents.length ? personalJoinedEvents.length : 0 }} 场</small>
                </article>
              </div>
            </div>
            <div v-else class="space-panel">
              <div class="panel-header">
                <div><h2>隐私设置</h2><p>管理你在社区里的可见范围</p></div>
                <span class="space-panel-kicker">{{ personalSpaceVisibility }}</span>
              </div>
              <div class="privacy-options">
                <button v-for="option in ['仅自己', '交流圈可见', '公开']" :key="option" :class="{ selected: personalSpaceVisibility === option }" @click="setPersonalPrivacy(option)">{{ option }}</button>
              </div>
              <p class="space-note">个人规划和 DDL 仍然默认私密，只展示你愿意分享的社区内容。</p>
            </div>
          </section>
          <aside class="space-aside">
            <section class="space-panel">
              <div class="panel-header">
                <div><h2>个人概览</h2><p>你的空间里都有哪些活动</p></div>
              </div>
              <div class="space-overview-list">
                <div><span>发帖</span><strong>{{ personalMyPosts.length }}</strong></div>
                <div><span>收藏</span><strong>{{ personalSavedPosts.length }}</strong></div>
                <div><span>小组</span><strong>{{ personalJoinedGroups.length }}</strong></div>
                <div><span>活动</span><strong>{{ personalJoinedEvents.length }}</strong></div>
              </div>
            </section>
            <section class="space-panel">
              <div class="panel-header">
                <div><h2>加入的小组</h2><p>你当前在交流圈里的位置</p></div>
              </div>
              <div v-if="personalJoinedGroups.length" class="space-list">
                <article v-for="group in personalJoinedGroups" :key="group.id" class="space-list-item">
                  <span :class="['community-group-icon', group.tone]">{{ group.icon }}</span>
                  <div><strong>{{ group.name }}</strong><small>{{ group.meta }}</small></div>
                </article>
              </div>
              <div v-else class="empty-state">还没有加入任何小组。</div>
            </section>
          </aside>
        </div>
      </div>
      <div v-else-if="activeView === '升学规划'" class="content-wrap annual-plan-page">
        <section class="page-heading">
          <div><p class="eyebrow"><GraduationCap :size="15" />个人长期规划</p><h1>年度规划 · {{ annualPlanYear }}</h1><p class="subheading">把长期目标拆成可执行的时间段和节点，只有你能查看与编辑。</p></div>
          <div class="annual-heading-actions"><button class="outline-button" @click="goToAnnualToday"><Clock3 :size="16" />回到今天</button><button class="primary-button" @click="openAnnualPlanEditor()"><Plus :size="17" />创建任务</button></div>
        </section>
        <section class="annual-controls">
          <div class="annual-zoom"><span>视图</span><button v-for="months in [3, 6, 9, 12]" :key="months" :class="{ selected: annualPlanZoom === months }" @click="setAnnualZoom(months)">{{ months }}个月</button></div>
          <div class="annual-slider"><input :value="annualPlanZoom" type="range" min="3" max="12" step="3" aria-label="时间轴缩放" @input="setAnnualZoom(Number($event.target.value))" /><div><button v-for="months in [3, 6, 9, 12]" :key="months" :class="{ selected: annualPlanZoom === months }" @click="setAnnualZoom(months)">{{ months }}个月</button></div></div>
          <div class="annual-range-controls"><button class="icon-button" aria-label="查看更早时间" title="查看更早时间" @click="shiftAnnualRange(-1)"><ChevronLeft :size="17" /></button><strong>{{ annualRangeLabel }}</strong><button class="icon-button" aria-label="查看更晚时间" title="查看更晚时间" @click="shiftAnnualRange(1)"><ChevronRight :size="17" /></button></div>
        </section>
        <div class="annual-legend"><button v-for="category in annualCategories" :key="category.id" :class="{ muted: !visibleAnnualCategories.includes(category.id) }" @click="toggleAnnualCategory(category.id)"><i :style="{ background: category.color }" />{{ category.icon }} {{ category.label }}</button></div>
        <p v-if="annualPlanError" class="dashboard-error">{{ annualPlanError }}</p>
        <section v-if="annualPlanLoading" class="annual-loading"><div /><div /><div /><div /><div /></section>
        <section v-else-if="!annualPlanTasks.length" class="annual-empty"><span>📭</span><h2>{{ annualPlanYear }} 年还没有规划任何任务</h2><p>从一个长期目标开始，把它拆成每一步可以完成的小事。</p><button class="primary-button" @click="openAnnualPlanEditor()"><Plus :size="16" />创建第一个年度任务</button></section>
        <section v-else class="annual-timeline-card">
          <div class="annual-months" :style="{ gridTemplateColumns: `repeat(${annualVisibleMonths.length}, minmax(0, 1fr))` }"><span v-for="month in annualVisibleMonths" :key="month.toISOString()">{{ month.getMonth() + 1 }}月</span></div>
          <div class="annual-timeline">
            <div class="annual-grid" :style="{ gridTemplateColumns: `repeat(${annualVisibleMonths.length}, minmax(0, 1fr))` }"><i v-for="month in annualVisibleMonths" :key="month.toISOString()" /></div>
            <button v-if="annualTodayPosition !== null" class="annual-today-marker" :style="{ left: `${annualTodayPosition}%` }" title="回到今天" @click="goToAnnualToday"><span>你在这里</span><div class="mini-student"><UserRound :size="17" /></div></button>
            <div v-for="category in annualCategories" :key="category.id" class="annual-category-row">
              <div class="annual-category-label"><span>{{ category.icon }}</span><strong>{{ category.label }}</strong></div>
              <div class="annual-category-track">
                <button v-for="task in annualVisibleTasks.filter((item) => item.category === category.id && item.type === 'period')" :key="task.id" :class="['annual-bar', task.status]" :style="annualTaskStyle(task)" :title="`${task.title} · ${task.startDate} 至 ${task.endDate}`" @click="annualPlanDetail = task"><span>{{ task.title }}</span><b v-if="task.subtaskTotal">{{ task.subtaskCompleted }}/{{ task.subtaskTotal }}</b></button>
                <button v-for="task in annualVisibleTasks.filter((item) => item.category === category.id && item.type === 'node')" :key="task.id" :class="['annual-node', task.status]" :style="annualTaskStyle(task)" :title="`${task.title} · ${task.nodeDate}`" @click="annualPlanDetail = task"><i /><span>{{ task.title }}</span></button>
              </div>
            </div>
          </div>
        </section>
        <footer class="annual-status-bar"><span>当前可见：{{ annualRangeLabel }}</span><span>任务总数：{{ annualPlanSummary.total }}</span><span>进行中：{{ annualPlanSummary.inProgress }}</span><span>已完成：{{ annualPlanSummary.completed }}</span></footer>
      </div>
    </main>
    <div v-if="showGlobalSearch" class="search-overlay" @click.self="closeGlobalSearch">
      <section class="global-search-panel">
        <div class="global-search-heading"><div><span class="card-kicker">快速查找</span><h2>搜索任务和课程</h2></div><button class="icon-button" aria-label="关闭搜索" @click="closeGlobalSearch"><X :size="19" /></button></div>
        <label class="global-search-input"><Search :size="17" /><input v-model="globalQuery" autofocus placeholder="输入任务、课程或发布者..." /></label>
        <div v-if="globalQuery.trim() && !globalSearchTaskResults.length && !globalSearchSubscriptionResults.length" class="notification-empty">没有找到匹配内容</div>
        <div v-else-if="globalQuery.trim()" class="global-search-results">
          <div v-if="globalSearchTaskResults.length"><span class="search-result-label">任务</span><button v-for="task in globalSearchTaskResults" :key="task.id" class="search-result" @click="openGlobalSearchTask(task)"><span class="source-icon">{{ task.source }}</span><span><strong>{{ task.title }}</strong><small>{{ task.date }} {{ task.time }} · {{ task.sourceName }}</small></span><ChevronRight :size="15" /></button></div>
          <div v-if="globalSearchSubscriptionResults.length"><span class="search-result-label">订阅课程</span><button v-for="item in globalSearchSubscriptionResults" :key="item.id" class="search-result" @click="openGlobalSearchSubscription(item)"><span class="subscription-result-icon">{{ item.type === '课程' ? '📚' : '🎓' }}</span><span><strong>{{ item.name }}</strong><small>{{ item.publisher }} · {{ item.count }} 个 DDL</small></span><ChevronRight :size="15" /></button></div>
        </div>
        <div v-else class="global-search-hint">输入关键词后，可直接打开任务详情或定位订阅课程。</div>
      </section>
    </div>
    <div v-if="homeComposerOpen" class="modal-backdrop" @click.self="homeComposerOpen = false">
      <form class="modal community-composer-modal" @submit.prevent="submitHomePost">
        <div class="modal-header">
          <div><span class="eyebrow"><UsersRound :size="15" />交流圈</span><h2>分享一个想法</h2></div>
          <button type="button" class="icon-button" aria-label="关闭分享窗口" @click="homeComposerOpen = false"><X :size="19" /></button>
        </div>
        <div class="composer-modal-user"><span class="community-avatar">{{ student.name.slice(0, 1) }}</span><div><strong>{{ student.name }}</strong><small>{{ student.school || '我的学校' }} · 仅展示给交流圈成员</small></div></div>
        <label>你想分享什么？<textarea v-model="homeComposerDraft" autofocus maxlength="1000" placeholder="可以分享学习进展、申请问题、竞赛机会，或向同学发起讨论..." /></label>
        <div class="composer-modal-footer"><small>{{ homeComposerDraft.length }}/1000</small><button class="primary-button" type="submit" :disabled="!homeComposerDraft.trim()">发布分享</button></div>
      </form>
    </div>
    <div v-if="taskEditorOpen && selectedTask" class="modal-backdrop" @click.self="taskEditorOpen = false">
      <form class="modal task-editor" @submit.prevent="saveTaskDetails">
        <div class="modal-header">
          <div><span class="eyebrow">{{ selectedTask.source }} {{ selectedTask.sourceName }}</span><h2>任务详情</h2></div>
          <button type="button" class="icon-button" aria-label="关闭" @click="taskEditorOpen = false"><X :size="19" /></button>
        </div>
          <div :class="['official-task', { 'personal-task-card': selectedTask.kind === 'personal' }]">
            <span class="readonly-label">{{ selectedTask.kind === 'personal' ? '个人任务' : '官方任务' }}</span>
            <h3>{{ selectedTask.title }}</h3>
            <p><Clock3 :size="14" />截止：{{ selectedTask.date }} {{ selectedTask.time }}</p>
            <small v-if="selectedTask.kind !== 'personal' && selectedTask.publisher">发布者：{{ selectedTask.publisher }}</small>
          </div>
        <label>任务状态
          <select v-model="taskEditor.status">
            <option value="todo">未开始</option><option value="doing">进行中</option><option value="done">已完成</option>
          </select>
        </label>
        <label>我的优先级
          <select v-model="taskEditor.priority">
            <option value="low">低</option><option value="normal">中</option><option value="high">高</option>
          </select>
        </label>
        <div class="schedule-editor">
          <div class="schedule-editor-heading"><strong>计划执行时间</strong><small>结束时间留空表示时间节点，最小 15 分钟</small></div>
          <label>日期<input v-model="taskEditor.planDate" type="date" /></label>
          <div class="form-two">
            <label>开始<input v-model="taskEditor.plannedStart" type="time" step="900" /></label>
            <label>结束<input v-model="taskEditor.plannedEnd" :disabled="taskEditorEndsAtMidnight" type="time" step="900" /></label>
          </div>
          <label class="schedule-midnight-toggle"><span>结束于当天 24:00</span><input v-model="taskEditorEndsAtMidnight" type="checkbox" /></label>
          <p v-if="taskEditor.plannedStart && (taskEditor.plannedEnd || taskEditorEndsAtMidnight)" class="schedule-duration">计划时长：{{ taskEditorDuration() }} 分钟</p>
        </div>
        <label>我的备注
          <textarea v-model="taskEditor.note" placeholder="例如：周三晚先完成提纲..." />
        </label>
        <div class="reminder-heading"><span>自定义提醒</span><button type="button" class="text-button" @click="addReminder"><Plus :size="14" />添加提醒</button></div>
        <div v-for="(reminder, index) in taskEditor.reminders" :key="`${index}-${reminder}`" class="reminder-row">
          <input v-model="taskEditor.reminders[index]" type="datetime-local" />
          <button type="button" class="icon-button" aria-label="删除提醒" @click="removeReminder(index)"><X :size="15" /></button>
        </div>
        <p v-if="!taskEditor.reminders.length" class="no-reminders">还没有设置提醒</p>
        <p v-if="taskEditorError" class="auth-error">{{ taskEditorError }}</p>
        <button class="primary-button full-button" type="submit" :disabled="taskEditorSaving">{{ taskEditorSaving ? '保存中...' : '保存我的安排' }}</button>
      </form>
    </div>
    <div v-if="showSettings" class="modal-backdrop" @click.self="showSettings = false">
      <form class="modal settings-modal" @submit.prevent="saveNotificationSettings">
        <div class="modal-header">
          <div><span class="eyebrow"><Settings2 :size="15" />通知设置</span><h2>提醒偏好</h2></div>
          <button type="button" class="icon-button" aria-label="关闭" @click="showSettings = false"><X :size="19" /></button>
        </div>
        <div v-if="settingsLoading" class="notification-empty">正在加载设置...</div>
        <template v-else>
          <label class="setting-toggle"><span><strong>截止前 24 小时提醒</strong><small>未完成任务会生成站内提醒</small></span><input v-model="notificationSettings.due24hEnabled" type="checkbox" /></label>
          <label class="setting-toggle"><span><strong>微信提醒</strong><small>{{ notificationSettings.wechatMode === 'log' ? '当前为本地模拟模式' : notificationSettings.wechatConfigured ? '已启用微信公众号通道' : '通道等待管理员配置' }}</small></span><input v-model="notificationSettings.wechatEnabled" :disabled="!notificationSettings.wechatConfigured" type="checkbox" /></label>
          <div class="wechat-binding-row"><div><strong>微信账号</strong><small>{{ notificationSettings.wechatBound ? '已绑定，可接收提醒' : '请在微信内完成授权绑定' }}</small></div><div class="wechat-actions"><button v-if="!notificationSettings.wechatBound && notificationSettings.wechatBindingAvailable" class="outline-button" type="button" @click="connectWeChat">绑定微信</button><button v-if="notificationSettings.wechatBound" class="text-button" type="button" :disabled="wechatTesting" @click="testWeChat">{{ wechatTesting ? '发送中...' : '发送测试' }}</button><span v-if="!notificationSettings.wechatBound" :class="['binding-status', { bound: notificationSettings.wechatBound }]">{{ notificationSettings.wechatBound ? '已绑定' : '未配置' }}</span></div></div>
          <label>我的标语<input v-model="profileMotto" maxlength="120" placeholder="例如：今天先完成最重要的一件事" /></label>
          <p class="settings-note">微信通道状态：{{ notificationSettings.wechatBound ? '已绑定' : '未绑定' }}</p>
          <div class="password-settings"><strong>修改密码</strong><small>使用至少 8 位、不常见的新密码。</small><div class="form-two"><label>当前密码<input v-model="passwordForm.currentPassword" autocomplete="current-password" type="password" /></label><label>新密码<input v-model="passwordForm.newPassword" autocomplete="new-password" minlength="8" type="password" /></label></div><button class="outline-button" type="button" :disabled="passwordSaving || !passwordForm.currentPassword || !passwordForm.newPassword" @click="changePassword">{{ passwordSaving ? '更新中...' : '更新密码' }}</button></div>
          <p v-if="settingsError" class="auth-error">{{ settingsError }}</p>
          <p v-if="settingsMessage" class="auth-message">{{ settingsMessage }}</p>
          <button class="primary-button full-button" type="submit" :disabled="settingsSaving">{{ settingsSaving ? '保存中...' : '保存提醒设置' }}</button>
        </template>
      </form>
    </div>
    <div v-if="friendProfile" class="modal-backdrop" @click.self="friendProfile = null">
      <section class="modal friend-profile-modal">
        <div class="modal-header">
          <div><span class="eyebrow"><UsersRound :size="15" />学习伙伴</span><h2>{{ friendProfile.name }}</h2></div>
          <button class="icon-button" aria-label="关闭好友资料" @click="friendProfile = null"><X :size="19" /></button>
        </div>
        <div class="friend-profile-summary">
          <span class="friend-avatar">{{ friendProfile.initials }}<i v-if="friendProfile.online" /></span>
          <div><strong>{{ friendProfile.school }} · {{ friendProfile.grade }}</strong><small>{{ friendProfile.bio }}</small></div>
        </div>
        <div class="friend-profile-facts"><span>{{ friendProfile.mutual || 0 }} 位共同好友</span><span>{{ friendProfile.online ? '当前在线' : '最近不在线' }}</span></div>
        <div class="modal-actions">
          <button v-if="friendProfile.status === 'friend' && chatPeer?.userId === friendProfile.id" class="outline-button" type="button" @click="toggleChatMute(); friendProfile = null">{{ chatPeer.muted ? '取消免打扰' : '免打扰' }}</button>
          <button v-if="friendProfile.status === 'friend' && chatPeer?.userId === friendProfile.id" class="danger-button" type="button" @click="blockChatPeer(); friendProfile = null">拉黑</button>
          <button v-if="friendProfile.status === 'friend' && chatPeer?.userId === friendProfile.id" class="text-button" type="button" @click="reportChatPeer(); friendProfile = null">举报</button>
          <button v-if="friendProfile.status === 'friend'" class="danger-button" type="button" @click="removeFriend(friendProfile); friendProfile = null">删除好友</button>
          <button v-if="friendProfile.status === 'friend'" class="primary-button" type="button" @click="openChatWithUser(friendProfile); friendProfile = null"><MessageCircle :size="15" />发消息</button>
          <button v-else-if="friendProfile.status === 'pending_received'" class="primary-button" type="button" @click="acceptFriendRequest(friendProfile); friendProfile = null">接受申请</button>
          <button v-else-if="friendProfile.status === 'pending_sent'" class="outline-button" type="button" @click="cancelFriendRequest(friendProfile); friendProfile = null">撤回申请</button>
          <button v-else class="primary-button" type="button" @click="sendFriendRequest(friendProfile); friendProfile = null"><Plus :size="15" />加好友</button>
        </div>
      </section>
    </div>
    <div v-if="chatGroupFormOpen" class="modal-backdrop" @click.self="chatGroupFormOpen = false">
      <form class="modal chat-group-form" @submit.prevent="createChatGroup">
        <div class="modal-header"><div><span class="eyebrow"><UsersRound :size="15" />学习小组</span><h2>创建一个小组</h2></div><button class="icon-button" type="button" aria-label="关闭创建小组" @click="chatGroupFormOpen = false"><X :size="19" /></button></div>
        <label>小组名称<input v-model="newChatGroup.name" autofocus maxlength="120" placeholder="例如：AP 微积分互助组" /></label>
        <label>小组类型<select v-model="newChatGroup.kind"><option value="learning">学习小组</option><option value="course">课程群</option><option value="event">活动群</option></select></label>
        <label>小组简介<textarea v-model="newChatGroup.description" maxlength="500" placeholder="写下小组的目标和交流范围..." /></label>
        <button class="primary-button full-button" type="submit" :disabled="!newChatGroup.name.trim()">创建并进入</button>
      </form>
    </div>
    <div v-if="chatGroupInviteOpen" class="modal-backdrop" @click.self="chatGroupInviteOpen = false">
      <section class="modal chat-group-invite-modal">
        <div class="modal-header">
          <div><span class="eyebrow"><UserPlus :size="15" />{{ chatGroup?.name }}</span><h2>邀请好友加入</h2></div>
          <button class="icon-button" type="button" aria-label="关闭邀请好友" title="关闭" @click="chatGroupInviteOpen = false"><X :size="19" /></button>
        </div>
        <p class="chat-group-invite-intro">邀请发出后，对方确认才会加入小组。</p>
        <p v-if="chatGroupInviteError" class="auth-error">{{ chatGroupInviteError }}</p>
        <div v-if="chatGroupInviteLoading" class="chat-group-invite-empty">正在加载你的好友...</div>
        <div v-else-if="chatGroupInviteCandidates.length" class="chat-group-invite-candidates">
          <article v-for="friend in chatGroupInviteCandidates" :key="friend.id">
            <span class="chat-list-avatar">{{ friend.initials }}</span>
            <div><strong>{{ friend.name }}</strong><small>{{ friend.school }} · {{ friend.grade }}</small></div>
            <button v-if="friend.pending" class="outline-button" type="button" disabled>已邀请</button>
            <button v-else class="primary-button" type="button" :disabled="chatGroupInviteSendingIds.includes(friend.id)" @click="inviteChatGroupFriend(friend)">{{ chatGroupInviteSendingIds.includes(friend.id) ? '发送中' : '邀请' }}</button>
          </article>
        </div>
        <div v-else class="chat-group-invite-empty">没有可邀请的好友。先添加学习伙伴，或等待对方处理已有邀请。</div>
        <div v-if="chatGroupPendingInvitations.length" class="chat-group-pending">
          <strong>等待确认</strong>
          <span v-for="invitation in chatGroupPendingInvitations" :key="invitation.id">{{ invitation.invitee.name }} · {{ invitation.createdAt }}</span>
        </div>
      </section>
    </div>
    <button v-if="activeView !== '升学规划'" class="floating-add" aria-label="创建个人待办" @click="openPersonalTaskCreate(activeView === '日历' ? selectedDate : today)"><Plus :size="25" /></button>
    <div v-if="showCreate" class="modal-backdrop" @click.self="showCreate = false"><form class="modal" @submit.prevent="savePersonalTask"><div class="modal-header"><div><span class="eyebrow">个人待办</span><h2>{{ editingPersonalTask ? '编辑个人待办' : '创建一个小目标' }}</h2></div><button type="button" class="icon-button" aria-label="关闭" @click="showCreate = false; resetPersonalTaskForm()"><X :size="19" /></button></div><label>要做什么？<input v-model="newTask.title" autofocus placeholder="例如：准备明天的演讲" /></label><div class="form-two"><label>截止日期<input v-model="newTask.due" type="date" /></label><label>截止时间<input v-model="newTask.dueTime" type="time" /></label></div><label>备注（可选）<textarea v-model="newTask.note" placeholder="写下你需要记住的内容..." /></label><div class="modal-actions"><button v-if="editingPersonalTask" type="button" class="danger-button" @click="deletePersonalTask">删除待办</button><button class="primary-button" type="submit">{{ editingPersonalTask ? '保存修改' : '添加到我的安排' }}</button></div></form></div>
    <div v-if="annualPlanEditorOpen" class="modal-backdrop" @click.self="annualPlanEditorOpen = false">
      <form class="modal annual-editor" @submit.prevent="saveAnnualPlanTask">
        <div class="modal-header"><div><span class="eyebrow">年度规划</span><h2>{{ editingAnnualPlanTask ? '编辑年度任务' : '创建年度任务' }}</h2></div><button type="button" class="icon-button" aria-label="关闭" @click="annualPlanEditorOpen = false"><X :size="19" /></button></div>
        <label>任务名称<input v-model="annualPlanForm.title" required autofocus placeholder="例如：牛剑申请季" /></label>
        <div class="form-two"><label>分类<select v-model="annualPlanForm.category"><option v-for="category in annualCategories" :key="category.id" :value="category.id">{{ category.icon }} {{ category.label }}</option></select></label><label>类型<select v-model="annualPlanForm.type"><option value="period">时间段任务</option><option value="node">时间节点</option></select></label></div>
        <div v-if="annualPlanForm.type === 'period'" class="form-two"><label>开始日期<input v-model="annualPlanForm.startDate" required type="date" /></label><label>结束日期<input v-model="annualPlanForm.endDate" required type="date" /></label></div>
        <label v-else>节点日期<input v-model="annualPlanForm.nodeDate" required type="date" /></label>
        <label>说明<textarea v-model="annualPlanForm.description" placeholder="写下这个目标的范围、资料或完成标准..." /></label>
        <p v-if="annualPlanError" class="auth-error">{{ annualPlanError }}</p>
        <div v-if="annualPlanDeletePending" class="annual-delete-confirm">
          <strong>确定删除“{{ annualPlanDeletePending.title }}”？</strong>
          <small>删除后无法恢复，任务下的子任务也会一起删除。</small>
          <div><button type="button" class="outline-button" @click="cancelDeleteAnnualPlanTask">取消</button><button type="button" class="danger-button" :disabled="annualPlanDeleting" @click="deleteAnnualPlanTask(annualPlanDeletePending)">{{ annualPlanDeleting ? '删除中...' : '确认删除' }}</button></div>
        </div>
        <div class="modal-actions"><button v-if="editingAnnualPlanTask && !annualPlanDeletePending" type="button" class="danger-button" @click.stop.prevent="requestDeleteAnnualPlanTask(editingAnnualPlanTask)">删除任务</button><button class="primary-button" type="button" :disabled="annualPlanSaving || annualPlanDeleting" @click.stop.prevent="saveAnnualPlanTask">{{ annualPlanSaving ? '保存中...' : '保存任务' }}</button></div>
      </form>
    </div>
    <div v-if="annualPlanDetail" class="modal-backdrop" @click.self="annualPlanDetail = null">
      <section class="modal annual-detail-modal">
        <div class="modal-header"><div><span class="eyebrow">{{ annualCategory(annualPlanDetail.category).icon }} {{ annualCategory(annualPlanDetail.category).label }} · {{ annualPlanDetail.type === 'period' ? '时间段任务' : '时间节点' }}</span><h2>{{ annualPlanDetail.title }}</h2></div><div class="annual-detail-actions"><button type="button" class="icon-button" aria-label="编辑年度任务" title="编辑年度任务" @click="openAnnualPlanEditor(annualPlanDetail)"><Pencil :size="16" /></button><button type="button" class="icon-button" aria-label="关闭" @click="annualPlanDetail = null"><X :size="19" /></button></div></div>
        <div class="annual-detail-meta"><span>{{ annualPlanDetail.type === 'period' ? `${annualPlanDetail.startDate} 至 ${annualPlanDetail.endDate}` : annualPlanDetail.nodeDate }}</span><span>{{ annualPlanDetail.status === 'completed' ? '已完成' : annualPlanDetail.status === 'in_progress' ? '进行中' : '未开始' }}</span></div>
        <p v-if="annualPlanDetail.description" class="annual-detail-description">{{ annualPlanDetail.description }}</p>
        <div class="annual-subtask-heading"><div><strong>任务拆分</strong><small>{{ annualPlanDetail.subtaskCompleted }}/{{ annualPlanDetail.subtaskTotal }} 已完成</small></div><div class="annual-subtask-progress"><i :style="{ width: `${annualPlanDetail.subtaskTotal ? annualPlanDetail.subtaskCompleted / annualPlanDetail.subtaskTotal * 100 : 0}%` }" /></div></div>
        <div class="annual-subtask-list">
          <div v-for="subtask in annualPlanDetail.subtasks" :key="subtask.id" :class="['annual-subtask', { completed: subtask.completed }]">
            <template v-if="editingAnnualPlanSubtaskId === subtask.id"><input v-model="annualPlanSubtaskEdit.title" autofocus /><input v-model="annualPlanSubtaskEdit.dueDate" type="date" /><button class="icon-button" aria-label="保存子任务" title="保存子任务" @click="saveAnnualPlanSubtask(subtask)"><Check :size="16" /></button><button class="icon-button" aria-label="取消编辑" title="取消编辑" @click="editingAnnualPlanSubtaskId = null"><X :size="16" /></button></template>
            <template v-else><button class="check-button" :aria-label="subtask.completed ? '标记为未完成' : '标记为完成'" @click="saveAnnualPlanSubtask(subtask, { completed: !subtask.completed })"><Check v-if="subtask.completed" :size="13" /></button><div><strong>{{ subtask.title }}</strong><small v-if="subtask.dueDate">{{ subtask.dueDate }}</small></div><button class="icon-button" aria-label="编辑子任务" title="编辑子任务" @click="editAnnualPlanSubtask(subtask)"><Pencil :size="15" /></button><button class="icon-button" aria-label="删除子任务" title="删除子任务" @click="deleteAnnualPlanSubtask(subtask)"><Trash2 :size="15" /></button></template>
          </div>
          <div v-if="!annualPlanDetail.subtasks.length" class="annual-no-subtasks">把大任务拆成几个可完成的小步骤吧。</div>
        </div>
        <form class="annual-add-subtask" @submit.prevent="addAnnualPlanSubtask"><input v-model="annualPlanSubtaskDraft.title" placeholder="添加子任务" /><input v-model="annualPlanSubtaskDraft.dueDate" type="date" /><button class="primary-button" type="submit"><Plus :size="15" />添加</button></form>
        <p v-if="annualPlanError" class="auth-error">{{ annualPlanError }}</p>
      </section>
    </div>
    <div v-if="chatImageViewer" class="chat-image-viewer" role="dialog" aria-modal="true" aria-label="聊天图片预览" @click.self="closeChatImage">
      <button class="icon-button chat-image-viewer-close" type="button" aria-label="关闭图片预览" title="关闭" @click="closeChatImage"><X :size="21" /></button>
      <img :src="chatImageViewer" alt="聊天图片大图" @click.stop />
    </div>
  </div>
</template>
