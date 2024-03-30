package com.balsdon.accessibilityDeveloperService

import android.accessibilityservice.AccessibilityButtonController
import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.Context
import android.content.IntentFilter
import android.graphics.Bitmap
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.Rect
import android.media.AudioManager
import android.os.Build
import android.os.Environment
import android.os.SystemClock
import android.support.wearable.watchface.accessibility.AccessibilityUtils
import android.util.Xml
import android.view.*
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityManager
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityNodeInfo.*
import android.widget.*
import androidx.annotation.IdRes
import androidx.annotation.RequiresApi
import androidx.core.view.accessibility.AccessibilityNodeInfoCompat
import com.balsdon.accessibilityBroadcastService.ACCESSIBILITY_CONTROL_BROADCAST_ACTION
import com.balsdon.accessibilityBroadcastService.AccessibilityActionReceiver
import com.balsdon.accessibilityBroadcastService.log
import com.balsdon.accessibilityDeveloperService.data.EventData
import org.xmlpull.v1.XmlSerializer
import java.io.*
import java.lang.Math.max
import java.lang.ref.WeakReference
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.thread
import kotlin.concurrent.withLock


/*
flagRequestAccessibilityButton: Will show the accessibility button on the bottom right hand side
 */
class AccessibilityDeveloperService : AccessibilityService() {
    enum class SelectionType {
        ELEMENT_ID, ELEMENT_TYPE, ELEMENT_TEXT, ELEMENT_HEADING
    }

    companion object {
        // https://developer.android.com/reference/android/content/BroadcastReceiver#peekService(android.content.Context,%20android.content.Intent)
        lateinit var instance: WeakReference<AccessibilityDeveloperService>
        const val DIRECTION_FORWARD = "DIRECTION_FORWARD"
        const val DIRECTION_BACK = "DIRECTION_BACK"
        private const val MAX_POSITION = 1000f
        private const val MIN_POSITION = 100f
        private const val IDLE_TIMEOUT = 10000
        private const val TRANSITION_TIMEOUT = 3000
        private const val IDLE_TIME = 1000


        // lock to prevent concurrent access to the a11yList
        val lock = ReentrantLock()
        val condition = lock.newCondition()
        var a11yList = ArrayList<AccessibilityEvent>()
        var waitingForEvent = false
        var mLastEventTimeMillis: Long = -1

        private val accessibilityButtonCallback =
            object : AccessibilityButtonController.AccessibilityButtonCallback() {
                override fun onClicked(controller: AccessibilityButtonController) {
                    log(
                        "AccessibilityDeveloperService",
                        "    ~~> AccessibilityButtonCallback"
                    )
                }

                override fun onAvailabilityChanged(
                    controller: AccessibilityButtonController,
                    available: Boolean
                ) {
                    log(
                        "AccessibilityDeveloperService",
                        "    ~~> AccessibilityButtonCallback availability [$available]"
                    )
                }
            }
    }

    private fun Context.AccessibilityManager() =
        getSystemService(Context.ACCESSIBILITY_SERVICE) as AccessibilityManager

    private val accessibilityActionReceiver = AccessibilityActionReceiver()
    private val audioManager: AudioManager by lazy { getSystemService(AUDIO_SERVICE) as AudioManager }

    private var curtainView: FrameLayout? = null

    private fun <T : View> findElement(@IdRes resId: Int): T =
        curtainView?.findViewById(resId)
            ?: throw RuntimeException("Required view not found: CurtainView")

    private val announcementTextView: TextView
        get() = findElement(R.id.announcementText)
    private val classNameTextView: TextView
        get() = findElement(R.id.className)
    private val enabledCheckBox: CheckBox
        get() = findElement(R.id.enabled)
    private val checkedCheckBox: CheckBox
        get() = findElement(R.id.checked)
    private val scrollableCheckBox: CheckBox
        get() = findElement(R.id.scrollable)
    private val passwordCheckBox: CheckBox
        get() = findElement(R.id.password)
    private val headingCheckBox: CheckBox
        get() = findElement(R.id.heading)
    private val editableCheckBox: CheckBox
        get() = findElement(R.id.editable)

    private val audioStream = AudioManager.STREAM_ACCESSIBILITY
    private var previousEvent = EventData()

    // REQUIRED overrides... not used
    override fun onInterrupt() = Unit

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null)
        {
            log("AccessibilityEvents", "NULL")
            return
        }

        log("AccessibilityEvents", "[$event]; view: [${event.source}]")

        lock.withLock {
            mLastEventTimeMillis = max(mLastEventTimeMillis, event.getEventTime())
            if (waitingForEvent) {
                a11yList.add(event)
            }
            condition.signalAll()
        }

        if (!event.text.isNullOrEmpty()) {
            previousEvent = EventData.from(event)
            showEvent(previousEvent)
        }
    }

    private fun showEvent(event: EventData) {
        if (curtainView == null) return
        announcementTextView.text = event.eventText
            .replace('[', ' ')
            .replace(']', ' ')
            .trim()

        classNameTextView.text = event.className
        passwordCheckBox.isChecked = event.isPassword
        enabledCheckBox.isChecked = event.isEnabled
        checkedCheckBox.isChecked = event.isChecked
        scrollableCheckBox.isChecked = event.isChecked

        headingCheckBox.isChecked = event.isHeading
        editableCheckBox.isChecked = event.isEditable
    }

    fun toggleCurtain() {
        val windowManager = getSystemService(WINDOW_SERVICE) as WindowManager

        if (curtainView == null) {
            curtainView = FrameLayout(this)
            val layoutParams = WindowManager.LayoutParams().apply {
                type = WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY
                format = PixelFormat.OPAQUE
                flags = flags or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                width = WindowManager.LayoutParams.MATCH_PARENT
                height = WindowManager.LayoutParams.MATCH_PARENT
                gravity = Gravity.TOP
            }
            val inflater = LayoutInflater.from(this)
            inflater.inflate(R.layout.accessibility_curtain, curtainView)
            windowManager.addView(curtainView, layoutParams)
            showEvent(previousEvent)
        } else {
            windowManager.removeView(curtainView)
            curtainView = null
        }
    }

    fun findFocusedViewInfo(): AccessibilityNodeInfoCompat = with(rootInActiveWindow) {
        val viewInfo = this.findFocus(FOCUS_ACCESSIBILITY)
        log(
            "AccessibilityDeveloperService",
            "  ~~> View in focus: [${viewInfo.className} : ${viewInfo.viewIdResourceName}]"
        )
        return AccessibilityNodeInfoCompat.wrap(viewInfo)
    }

    override fun onServiceConnected() {
        log(
            "AccessibilityDeveloperService",
            "onServiceConnected"
        )
        registerReceiver(accessibilityActionReceiver, IntentFilter().apply {
            addAction(ACCESSIBILITY_CONTROL_BROADCAST_ACTION)
            priority = 100
            log(
                "AccessibilityDeveloperService",
                "    ~~> Receiver is registered."
            )
        })
        instance = WeakReference(this)

        //https://developer.android.com/guide/topics/ui/accessibility/service
        if (accessibilityButtonController.isAccessibilityButtonAvailable) {
            accessibilityButtonController.registerAccessibilityButtonCallback(
                accessibilityButtonCallback
            )
        }
    }

    private fun dfsTree(
        currentNode: AccessibilityNodeInfo = rootInActiveWindow,
        depth: Int = 0
    ): List<Pair<AccessibilityNodeInfo, Int>> {
        val list = mutableListOf(Pair(currentNode, depth))
        if (currentNode.childCount > 0) {
            for (index in 0 until currentNode.childCount) {
                list.addAll(dfsTree(currentNode.getChild(index), depth + 1))
            }
        }
        return list
    }

    fun announceText(speakText: String) =
        AccessibilityManager().apply {
            sendAccessibilityEvent(AccessibilityEvent.obtain().apply {
                eventType = AccessibilityEvent.TYPE_ANNOUNCEMENT
                text.add(speakText)
            })
        }

    private fun focusBy(next: Boolean? = null, comparison: (AccessibilityNodeInfo) -> Boolean) {
        val tree = if (next == false) dfsTree().asReversed() else dfsTree()
        val currentNode = this.findFocus(FOCUS_ACCESSIBILITY)
        if (currentNode == null) {
            val firstNode = tree.firstOrNull { comparison(it.first) }
            firstNode?.first?.performAction(ACTION_ACCESSIBILITY_FOCUS)
            return
        }

        val index = tree.indexOfFirst { it.first == currentNode }
        if (next == null) {
            for (currentIndex in tree.indices) {
                if (comparison(tree[currentIndex].first)) {
                    tree[currentIndex].first.performAction(ACTION_ACCESSIBILITY_FOCUS)
                    return
                }
            }
        } else {
            for (currentIndex in index + 1 until tree.size) {
                if (comparison(tree[currentIndex].first)) {
                    tree[currentIndex].first.performAction(ACTION_ACCESSIBILITY_FOCUS)
                    return
                }
            }
        }
    }

    //TODO: Bug [02]: Need to scroll to element if it's not in view
    @OptIn(ExperimentalStdlibApi::class)
    fun focus(type: SelectionType, value: String, next: Boolean = true) {
        when (type) {
            SelectionType.ELEMENT_ID -> focusBy(null) {
                it.viewIdResourceName?.lowercase()?.contains(value.lowercase()) ?: false
            }
            SelectionType.ELEMENT_TEXT -> focusBy(null) {
                it.text?.toString()?.lowercase()?.contains(value.lowercase()) ?: false
            }
            SelectionType.ELEMENT_TYPE -> focusBy(next) { it.className == value }
            SelectionType.ELEMENT_HEADING -> focusBy(next) { it.isHeading }
        }
    }

    @RequiresApi(Build.VERSION_CODES.R)
    fun swipeHorizontalWaitCapture(rightToLeft: Boolean, broadcastId: String) {
        thread {
            log("swipeHorizontalWaitCapture", "start to swipeHorizontalWaitCapture")
            lock.withLock {
                waitingForEvent = true
                a11yList.clear()
            }
            performGesture(
                GestureAction(createHorizontalSwipePath(rightToLeft)),
                broadcastId = broadcastId
            )

            var receivedEvents = ArrayList<String>()
            try {
                var startTime = SystemClock.uptimeMillis()
                while (true) {
                    var localEvents = ArrayList<AccessibilityEvent>()
                    lock.withLock {
                        localEvents.addAll(a11yList)
                        if (a11yList.size > 0) {
                            a11yList.clear()
                        }
                    }
                    while (!localEvents.isEmpty()) {
                        var e = localEvents.removeAt(0)
                        receivedEvents.add(e.eventType.toString())
                        if (e.eventTime < startTime) {
                            continue
                        }
                        if (e.eventType == AccessibilityEvent.TYPE_WINDOWS_CHANGED ||
                            e.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||
                            e.eventType == AccessibilityEvent.TYPE_VIEW_ACCESSIBILITY_FOCUSED
                        ) {
                            throw Exception("window transition observed ")
                        }
                    }
                    var pastTime = SystemClock.uptimeMillis() - startTime
                    if (pastTime > TRANSITION_TIMEOUT) {
                        throw Exception("Event not received, we are in timeout " + pastTime.toString())
                    }
                }
            } catch (e: Exception) {
                log("swipeHorizontalWaitCapture", "swipeHorizontalWaitCapture exception for " + broadcastId + ": " + e)
                dumpA11yTree(broadcastId)
                takeScreenshot(broadcastId)
            } finally {
                lock.withLock {
                    waitingForEvent = false
                    condition.signalAll()
                    a11yList.clear()
                }
            }
        }
    }

    @RequiresApi(Build.VERSION_CODES.R)
    fun captureWhenIdle(broadcastId: String) {
        thread {
            log("captureWhenIdle", "start to captureWhenIdle")

            try {
                var startTime = SystemClock.uptimeMillis()
                lock.withLock {
                    if (mLastEventTimeMillis <= 0) {
                        mLastEventTimeMillis = startTime
                    }
                }
                while (true) {
                    var curTime = SystemClock.uptimeMillis()
                    if (curTime - startTime > IDLE_TIMEOUT) {
                        throw Exception("IDLE timeout " + (curTime - startTime).toString())
                    }
                    if (curTime - mLastEventTimeMillis > IDLE_TIME) {
                        throw Exception("IDLE observed $curTime, $mLastEventTimeMillis " + (curTime - mLastEventTimeMillis).toString())
                    }

                }
            } catch (e: Exception) {
                log("captureWhenIdle", "captureWhenIdle exception for " + broadcastId + ": " + e)
                takeScreenshot(broadcastId)
            } finally {

            }
        }
    }
    @RequiresApi(Build.VERSION_CODES.R)
    fun clickWaitCapture(broadcastId: String) {
        thread {
            log("clickWaitCapture", "start to clickWaitCapture")
            lock.withLock {
                waitingForEvent = true
                a11yList.clear()
            }

            val res = findFocusedViewInfo().performAction(ACTION_CLICK)
            log("clickWaitCapture", "clickWaitCapture res for " + broadcastId + ": " + res)
            var receivedEvents = ArrayList<String>()
            try {
                var startTime = SystemClock.uptimeMillis()//System.currentTimeMillis()
                log("TTT:AccessibilityEvents", startTime.toString())
                while (true) {
                    var localEvents = ArrayList<AccessibilityEvent>()
                    lock.withLock {
                        localEvents.addAll(a11yList)
                        if (a11yList.size > 0) {
                            a11yList.clear()
                        }
                    }
                    while (!localEvents.isEmpty()) {
                        var e = localEvents.removeAt(0)
                        if (e.eventTime < startTime) {
                            continue
                        }
                        if (e.eventType == AccessibilityEvent.TYPE_WINDOWS_CHANGED ||
                            e.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||
                            e.eventType == AccessibilityEvent.TYPE_VIEW_ACCESSIBILITY_FOCUSED
                        ) {
                            throw Exception("window transition observed " )
                        }
                    }
                    var pastTime = SystemClock.uptimeMillis() - startTime
                    if (pastTime > TRANSITION_TIMEOUT) {
                        throw Exception("Event not received, we are in timeout " + pastTime.toString())
                    }

                }
            } catch (e: Exception) {
                log("clickWaitCapture", "clickWaitCapture exception: " + e.toString())

                dumpA11yTree(broadcastId)
                takeScreenshot(broadcastId)
            } finally {

                lock.withLock {
                    waitingForEvent = false
                    condition.signalAll()
                    a11yList.clear()
                }
            }

        }
    }
    @RequiresApi(Build.VERSION_CODES.R)
    private fun takeScreenshot(name:String) {
        takeScreenshot(
            Display.DEFAULT_DISPLAY,
            applicationContext.mainExecutor, @RequiresApi(Build.VERSION_CODES.R)
            object : TakeScreenshotCallback {
                @RequiresApi(api = Build.VERSION_CODES.R)
                override fun onSuccess(screenshotResult: ScreenshotResult) {
                    log("ScreenShotResult", "onSuccess")
                    val bitmap = Bitmap.wrapHardwareBuffer(
                        screenshotResult.hardwareBuffer,
                        screenshotResult.colorSpace
                    )
                    if (bitmap != null) {
                        saveImage(bitmap, "$name.png")
                    }
                }

                override fun onFailure(i: Int) {
                    log("ScreenShotResult", "onFailure code is $i")
                }
            })
    }

    private fun saveImage(finalBitmap: Bitmap, name:String) {
        val file = File(baseContext.filesDir.path, name)
        if (file.exists()) file.delete()
        try {
            val out = FileOutputStream(file)
            finalBitmap.compress(Bitmap.CompressFormat.PNG, 90, out)
            log("Screenshot", "dumped to " + file.absolutePath)
            out.flush()
            out.close()
        } catch (e: java.lang.Exception) {
            e.printStackTrace()
        }
    }

    fun click(long: Boolean = false, broadcastId: String) {
        thread {
            log("click", "start to click")
            val res =
                findFocusedViewInfo().performAction(if (long) ACTION_LONG_CLICK else ACTION_CLICK)
            log("click", "clicking res for " + broadcastId + ": " + res)
        }
    }

    fun commonDocumentDirPath(FolderName: String): File? {
        var dir: File? = null
        dir = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS)
                    .toString() + "/" + FolderName
            )
        } else {
            File(Environment.getExternalStorageDirectory().toString() + "/" + FolderName)
        }

        // Make sure the path directory exists.
        if (!dir.exists()) {
            // Make it, if it doesn't exit
            val success = dir.mkdirs()
            if (!success) {
                dir = null
            }
        }
        log("dump", Environment.getExternalStorageDirectory().toString())
        return dir
    }


    fun dumpA11yTree(broadcastID: String) {
        var LOG_TAG = "DumpResultCallback"
        log(LOG_TAG, "start to dump")
        val startTime = SystemClock.uptimeMillis()

        val file = File(baseContext.filesDir.path, "a11y3-$broadcastID.xml")

        val outputStream: OutputStream = FileOutputStream(file)
        val writer = OutputStreamWriter(outputStream)
        val serializer: XmlSerializer = Xml.newSerializer()
        val stringWriter = StringWriter()
        serializer.setOutput(stringWriter)
        serializer.startDocument("UTF-8", true)
        serializer.startTag("", "hierarchy")
        dumpNodeRec(rootInActiveWindow, serializer, 0)
        serializer.endTag("", "hierarchy")
        serializer.endDocument()
        writer.write(stringWriter.toString())
        writer.close()
        log(broadcastID, "DUMP 200", true)
        log(LOG_TAG, "dumped to " + file.absolutePath)
        val endTime = SystemClock.uptimeMillis();
        log(LOG_TAG, "Fetch time: " + (endTime - startTime) + "ms")
    }

    /**
     * The list of classes to exclude my not be complete. We're attempting to
     * only reduce noise from standard layout classes that may be falsely
     * configured to accept clicks and are also enabled.
     *
     * @param node
     * @return true if node is excluded.
     */
    private fun nafExcludedClass(node: AccessibilityNodeInfo): Boolean {
        val className = safeCharSeqToString(node.className)
        val NAF_EXCLUDED_CLASSES = arrayOf(
            GridView::class.java.name, GridLayout::class.java.name,
            ListView::class.java.name, TableLayout::class.java.name
        )
        for (excludedClassName in NAF_EXCLUDED_CLASSES) {
            if (className!!.endsWith(excludedClassName)) return true
        }
        return false
    }

    /**
     * We're looking for UI controls that are enabled, clickable but have no
     * text nor content-description. Such controls configuration indicate an
     * interactive control is present in the UI and is most likely not
     * accessibility friendly. We refer to such controls here as NAF controls
     * (Not Accessibility Friendly)
     *
     * @param node
     * @return false if a node fails the check, true if all is OK
     */
    private fun nafCheck(node: AccessibilityNodeInfo): Boolean {
        val isNaf = (node.isClickable && node.isEnabled
                && safeCharSeqToString(node.contentDescription)!!.isEmpty()
                && safeCharSeqToString(node.text)!!.isEmpty())
        return if (!isNaf) true else childNafCheck(node)
        // check children since sometimes the containing element is clickable
        // and NAF but a child's text or description is available. Will assume
        // such layout as fine.
    }

    /**
     * This should be used when it's already determined that the node is NAF and
     * a further check of its children is in order. A node maybe a container
     * such as LinerLayout and may be set to be clickable but have no text or
     * content description but it is counting on one of its children to fulfill
     * the requirement for being accessibility friendly by having one or more of
     * its children fill the text or content-description. Such a combination is
     * considered by this dumper as acceptable for accessibility.
     *
     * @param node
     * @return false if node fails the check.
     */
    private fun childNafCheck(node: AccessibilityNodeInfo): Boolean {
        val childCount = node.childCount
        for (x in 0 until childCount) {
            val childNode = node.getChild(x)
            if (childNode == null) {
                log(
                    "dump a11y child naf check", String.format(
                        "Null child %d/%d, parent: %s",
                        x, childCount, node.toString()
                    )
                )
                continue
            }
            if (!safeCharSeqToString(childNode.contentDescription)!!.isEmpty()
                || !safeCharSeqToString(childNode.text)!!.isEmpty()
            ) return true
            if (childNafCheck(childNode)) return true
        }
        return false
    }
    @Throws(IOException::class)
    private fun dumpNodeRec(node: AccessibilityNodeInfo, serializer: XmlSerializer, index: Int) {


        serializer.startTag("", "node")
        serializer.attribute("", "index", Integer.toString(index))
        serializer.attribute("", "resource-id", safeCharSeqToString(node.viewIdResourceName))
        serializer.attribute("", "text", safeCharSeqToString(node.text))
        serializer.attribute("", "class", safeCharSeqToString(node.className))
        serializer.attribute("", "package", safeCharSeqToString(node.packageName))
        serializer.attribute("", "content-desc", safeCharSeqToString(node.contentDescription))
        serializer.attribute("", "checkable", java.lang.Boolean.toString(node.isCheckable))
        serializer.attribute("", "checked", java.lang.Boolean.toString(node.isChecked))
        serializer.attribute("", "clickable", java.lang.Boolean.toString(node.isClickable))
        serializer.attribute("", "enabled", java.lang.Boolean.toString(node.isEnabled))
        serializer.attribute("", "focusable", java.lang.Boolean.toString(node.isFocusable))
        serializer.attribute("", "importantForAccessibility", java.lang.Boolean.toString(node.isImportantForAccessibility))
        serializer.attribute("", "focused", java.lang.Boolean.toString(node.isFocused))
        serializer.attribute("", "a11yFocused", java.lang.Boolean.toString(node.isAccessibilityFocused))
        serializer.attribute("", "scrollable", java.lang.Boolean.toString(node.isScrollable))
        serializer.attribute("", "long-clickable", java.lang.Boolean.toString(node.isLongClickable))
        serializer.attribute("", "password", java.lang.Boolean.toString(node.isPassword))
        serializer.attribute("", "selected", java.lang.Boolean.toString(node.isSelected))
        serializer.attribute("", "visible", java.lang.Boolean.toString(node.isVisibleToUser))
        serializer.attribute("", "invalid", java.lang.Boolean.toString(node.isContentInvalid))
        serializer.attribute("", "liveRegion", Integer.toString(node.liveRegion))
        serializer.attribute("", "drawingOrder", Integer.toString(node.drawingOrder))
//        serializer.attribute("", "hasInitFocus", java.lang.Boolean.toString(node.hasRequestInitialAccessibilityFocus()))
        val sb = StringBuilder()
        node.actionList.forEach { sb.append(it.id).append("-")}
        val string = sb.removeSuffix("-").toString()
        serializer.attribute("", "actionList", string)
        if (!nafExcludedClass(node) && !nafCheck(node))
            serializer.attribute("", "NAF", java.lang.Boolean.toString(true))
        val bounds = Rect()
        node.getBoundsInScreen(bounds)
        serializer.attribute("", "bounds", bounds.toShortString())
        val count = node.childCount
        for (i in 0 until count) {
            val child = node.getChild(i)
            if (child != null) {
                dumpNodeRec(child, serializer, i)
                child.recycle()
            } else {
                log(
                    "dumpA11yTree", String.format(
                        "Null child %d/%d, parent: %s",
                        i, count, node.toString()
                    )
                )
            }
        }
        serializer.endTag("", "node")
    }

    private fun safeCharSeqToString(cs: CharSequence?): String? {
        return cs?.let { stripInvalidXMLChars(it) } ?: ""
    }

    private fun stripInvalidXMLChars(cs: CharSequence): String? {
        val ret = StringBuffer()
        var ch: Char
        /* http://www.w3.org/TR/xml11/#charsets
        [#x1-#x8], [#xB-#xC], [#xE-#x1F], [#x7F-#x84], [#x86-#x9F], [#xFDD0-#xFDDF],
        [#x1FFFE-#x1FFFF], [#x2FFFE-#x2FFFF], [#x3FFFE-#x3FFFF],
        [#x4FFFE-#x4FFFF], [#x5FFFE-#x5FFFF], [#x6FFFE-#x6FFFF],
        [#x7FFFE-#x7FFFF], [#x8FFFE-#x8FFFF], [#x9FFFE-#x9FFFF],
        [#xAFFFE-#xAFFFF], [#xBFFFE-#xBFFFF], [#xCFFFE-#xCFFFF],
        [#xDFFFE-#xDFFFF], [#xEFFFE-#xEFFFF], [#xFFFFE-#xFFFFF],
        [#x10FFFE-#x10FFFF].
         */for (i in 0 until cs.length) {
            ch = cs[i]
            if (ch.toInt() >= 0x1 && ch.toInt() <= 0x8 || ch.toInt() >= 0xB && ch.toInt() <= 0xC || ch.toInt() >= 0xE && ch.toInt() <= 0x1F ||
                ch.toInt() >= 0x7F && ch.toInt() <= 0x84 || ch.toInt() >= 0x86 && ch.toInt() <= 0x9f ||
                ch.toInt() >= 0xFDD0 && ch.toInt() <= 0xFDDF || ch.toInt() >= 0x1FFFE && ch.toInt() <= 0x1FFFF ||
                ch.toInt() >= 0x2FFFE && ch.toInt() <= 0x2FFFF || ch.toInt() >= 0x3FFFE && ch.toInt() <= 0x3FFFF ||
                ch.toInt() >= 0x4FFFE && ch.toInt() <= 0x4FFFF || ch.toInt() >= 0x5FFFE && ch.toInt() <= 0x5FFFF ||
                ch.toInt() >= 0x6FFFE && ch.toInt() <= 0x6FFFF || ch.toInt() >= 0x7FFFE && ch.toInt() <= 0x7FFFF ||
                ch.toInt() >= 0x8FFFE && ch.toInt() <= 0x8FFFF || ch.toInt() >= 0x9FFFE && ch.toInt() <= 0x9FFFF ||
                ch.toInt() >= 0xAFFFE && ch.toInt() <= 0xAFFFF || ch.toInt() >= 0xBFFFE && ch.toInt() <= 0xBFFFF ||
                ch.toInt() >= 0xCFFFE && ch.toInt() <= 0xCFFFF || ch.toInt() >= 0xDFFFE && ch.toInt() <= 0xDFFFF ||
                ch.toInt() >= 0xEFFFE && ch.toInt() <= 0xEFFFF || ch.toInt() >= 0xFFFFE && ch.toInt() <= 0xFFFFF ||
                ch.toInt() >= 0x10FFFE && ch.toInt() <= 0x10FFFF
            ) ret.append(".") else ret.append(ch)
        }
        return ret.toString()
    }

    private fun createVerticalSwipePath(downToUp: Boolean): Path = Path().apply {
        if (downToUp) {
            moveTo(MAX_POSITION / 2, MAX_POSITION)
            lineTo(MAX_POSITION / 2, MIN_POSITION)
        } else {
            moveTo(MAX_POSITION / 2, MIN_POSITION)
            lineTo(MAX_POSITION / 2, MAX_POSITION)
        }
    }

    private fun createHorizontalSwipePath(rightToLeft: Boolean): Path = Path().apply {
        if (rightToLeft) {
            moveTo(MAX_POSITION, MAX_POSITION / 2)
            lineTo(MIN_POSITION, MAX_POSITION / 2)
        } else {
            moveTo(MIN_POSITION, MAX_POSITION / 2)
            lineTo(MAX_POSITION, MAX_POSITION / 2)
        }
    }

    fun swipeHorizontal(rightToLeft: Boolean, broadcastId: String) =
        performGesture(
            GestureAction(createHorizontalSwipePath(rightToLeft)),
            broadcastId = broadcastId
        )

    fun swipeVertical(downToUp: Boolean = true, broadcastId: String) =
        performGesture(GestureAction(createVerticalSwipePath(downToUp)),
            broadcastId = broadcastId)


//    fun threeFingerSwipeUp(broadcastId: String) {
//        val stX = halfWidth - quarterWidth
//        val stY = halfHeight + quarterHeight
//        val enY = halfHeight - quarterHeight
//        val eighth = quarterWidth / 2f
//
//        val one = Path().apply {
//            moveTo(stX - eighth, stY)
//            lineTo(stX - eighth, enY)
//        }
//        val two = Path().apply {
//            moveTo(stX, stY)
//            lineTo(stX, enY)
//        }
//        val three = Path().apply {
//            moveTo(stX + eighth, stY)
//            lineTo(stX + eighth, enY)
//        }
//
//        performGesture(
//            GestureAction(one),
//            GestureAction(two),
//            GestureAction(three),
//            broadcastId = broadcastId
//        )
//    }

    //https://developer.android.com/guide/topics/ui/accessibility/service#continued-gestures
    fun swipeUpRight(broadcastId: String) {
        val swipeUpAndRight = Path().apply {
            moveTo(MIN_POSITION, MAX_POSITION)
            lineTo(MIN_POSITION, MIN_POSITION)
            lineTo(MAX_POSITION, MIN_POSITION)
        }
        performGesture(GestureAction(swipeUpAndRight), broadcastId = broadcastId)
    }

    fun swipeUpLeft(broadcastId: String) {

        val swipeUpLeft = Path().apply {
            moveTo(MAX_POSITION/2, MAX_POSITION)
            lineTo(MAX_POSITION/2, MIN_POSITION)
            lineTo(MIN_POSITION, MIN_POSITION)
        }

        performGesture(
            GestureAction(swipeUpLeft,0,300),
            broadcastId = broadcastId
        )
    }


    private fun performGesture(vararg gestureActions: GestureAction, broadcastId: String, capture: Boolean = false) =
        dispatchGesture(
            createGestureFrom(*gestureActions),
            GestureResultCallback(broadcastId, this.findFocus(FOCUS_ACCESSIBILITY), this, capture),
            null
        )


    class GestureResultCallback(
        broadcastId: String,
        preFocus: AccessibilityNodeInfo,
        ctx: AccessibilityDeveloperService,
        capture: Boolean
    ) :
        AccessibilityService.GestureResultCallback() {

        private var gBroadcastId = broadcastId
        private var gPreFocus = preFocus
        private var gCapture = capture
        private var ctx = ctx
        @RequiresApi(Build.VERSION_CODES.R)
        override fun onCompleted(gestureDescription: GestureDescription?) {
            if (gCapture)
            {
                ctx.dumpA11yTree(gBroadcastId)
                ctx.takeScreenshot(gBroadcastId)

            }
            //  swiped and focus changed return code=200; swiped but focus remain unchanged return code=204
//            sleep(100) // WEIRDLY sometimes the focused node is not updated in this method
//
//            var code: Int
//            var node = ctx.findFocus(FOCUS_ACCESSIBILITY)
//
//            code = if (node == null)
//                206
//            else if(instance == null){
//                208
//            }
//            else {
//                var focus_bounds = Rect()
//                node.getBoundsInScreen(focus_bounds)
//                var pre_bounds = Rect()
//                gPreFocus.getBoundsInScreen(pre_bounds)
//                if (focus_bounds.equals(pre_bounds))
//                    204
//                else
//                    200
//            }
            var code = 200
            log(gBroadcastId, "SWIPE $code", true)
            super.onCompleted(gestureDescription)
        }

        override fun onCancelled(gestureDescription: GestureDescription?) {
            log("GestureResultCallback", "SWIPE 400")
            super.onCancelled(gestureDescription)
        }
    }

    // default to lower in case you forget
// because everyone LOVES accessibility over VC and in the [home] office
    fun adjustVolume(raise: Boolean = false) {
        audioManager.adjustStreamVolume(
            AudioManager.STREAM_ACCESSIBILITY,
            if (raise) AudioManager.ADJUST_RAISE else AudioManager.ADJUST_LOWER,
            AudioManager.FLAG_SHOW_UI
        )
    }

    val log_tag = "AccessibilityDeveloperService"

    fun setVolume(percent: Int) {
        require(percent <= 100) { " percent must be an integer less than 100" }
        require(percent >= 0) { " percent must be an integer greater than 0" }
        val max = audioManager.getStreamMaxVolume(audioStream)
        val volume = (max * (percent.toFloat() / 100f)).toInt()
        log(log_tag, "  ~~> Volume set to value [$volume]")
        audioManager.setStreamVolume(
            audioStream,
            volume,
            AudioManager.FLAG_SHOW_UI
        )
    }

    override fun onDestroy() {
        log(
            log_tag,
            "  ~~> onDestroy"
        )
        // Unregister accessibilityActionReceiver when destroyed.
        // I have had bad luck with broadcast receivers in the past
        try {
            unregisterReceiver(accessibilityActionReceiver)
            accessibilityButtonController.unregisterAccessibilityButtonCallback(
                accessibilityButtonCallback
            )
            log(
                log_tag,
                "    ~~> Receiver is unregistered.\r\n    ~~> AccessibilityButtonCallback is unregistered."
            )
        } catch (e: Exception) {
            log(
                log_tag,
                "    ~~> Unregister exception: [$e]"
            )
        } finally {
            super.onDestroy()
        }
    }
}