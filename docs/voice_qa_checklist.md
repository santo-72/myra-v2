# M.Y.R.A AI v2: Manual Voice Quality & TTS Realism QA Checklist

Use this QA test bench after any TTS voice configuration, prompt modification, or prosody tuning. Verify that M.Y.R.A speaks with broadcast-quality diction, syllable-by-syllable precision, and natural conversational cadence without robotic tone drops.

---

## 📋 Test Bench: 15 Representative Bengali Sentences

### Section 1: Polite Confirmations & Basic Greetings (নম্র সম্বোধন ও নিশ্চিতকরণ)
1. **Greeting & Status:** 
   * "শুভ অপরাহ্ন স্যার! আমি মাইরা, আপনার পার্সোনাল এআই অ্যাসিস্ট্যান্ট সম্পূর্ণ প্রস্তুত আছি। বলুন, আজ আপনাকে কীভাবে সাহায্য করতে পারি?"
   * **QA Check:** Warm vocal tone (Aoede), precise articulation of "অপরাহ্ন" and "অ্যাসিস্ট্যান্ট", no rushing.
2. **Action Confirmation:**
   * "ঠিক আছে স্যার, আমি আপনার নির্দেশ অনুযায়ী কাজটি শুরু করছি। দয়া করে কিছুক্ষণ অপেক্ষা করুন।"
   * **QA Check:** Gentle cadence, distinct pausing at commas.

### Section 2: Numbers, Financial Units, Dates & Times (সংখ্যা, তারিখ ও সময়)
3. **Data Storage & Sizes (Dynamic Reading):**
   * "আপনার কম্পিউটারের ড্রাইভ স্ক্যান করে দেখলাম, সেখানে প্রায় সাড়ে চার গিগাবাইট জায়গা খালি আছে এবং ফাইলটি ডাউনলোড করতে মাত্র তিন দশমিক আট মেগাবাইট লাগবে।"
   * **QA Check:** Natural reading of "সাড়ে চার গিগাবাইট" (4.5 GB) and "তিন দশমিক আট মেগাবাইট" (3.8 MB). Precise pronunciation of "দেখলাম" (Dekhlam).
4. **Dates & Schedules:**
   * "আজ সাতাশে জুলাই, সোমবার, দুপুর একটা বেজে পঁয়ত্রিশ মিনিট। আপনার পরবর্তী মিটিং ঠিক বিকেল চারটায় নির্ধারিত আছে।"
   * **QA Check:** Clear numerical expression of dates and times in modern standard Bengali.
5. **Financial Totals:**
   * "রিপোর্টের হিসাব অনুযায়ী, এই মাসে মোট খরচ হয়েছে দুই হাজার সাতশো পঞ্চাশ টাকা, যা আগের তুলনায় কিছুটা কম।"
   * **QA Check:** Smooth narration of currency figures without stumbling on verb endings like "হয়েছে".

### Section 3: Technical Identifiers & File Paths (ফাইল পাথ ও টেকনিক্যাল টার্ম)
6. **File Path Narration:**
   * "আমি আপনার প্রজেক্টের অ্যাপ কোর ফোল্ডারের ভেতরের জেমিনাই লাইভ ক্লায়েন্ট ডট পাই ফাইলটিতে প্রয়োজনীয় কোড পরিবর্তন করেছি।"
   * **QA Check:** Natural phrasing of file paths (`app/core/gemini_live_client.py`) without mechanically reciting forward slashes or underscores.
7. **Database Audit Status:**
   * "লোকাল এসকিউএলআইটি ডেটাবেসের ভেতর কন্টাক্টস এবং কনভার্সেশন লগস টেবিলগুলো সফলভাবে ইনিশিয়ালাইজ করা হয়েছে।"
   * **QA Check:** Seamless transition between English SQLite/database names and Bengali sentence verb structures ("হয়েছে").

### Section 4: Bilingual Code-Switching & Software Apps (মিশ্র ইংরেজি-বাংলা উচ্চারণ)
8. **Messaging Apps:**
   * "আমি হোয়াটসঅ্যাপ, মেসেঞ্জার এবং টেলিগ্রামের মাধ্যমে আপনার নির্বাচিত কন্টাক্টকে বার্তাটি পাঠিয়ে দিয়েছি।"
   * **QA Check:** Crisp articulation of WhatsApp, Messenger, and Telegram without unnatural pauses.
9. **Automation Tools & Libraries:**
   * "পাইথনের প্লে-রাইট এবং কাস্টম টিকিন্টার লাইব্রেরি ব্যবহার করে স্ক্রিন স্ট্রিম এবং ব্যাকগ্রাউন্ড টাস্কগুলো স্বয়ংক্রিয়ভাবে চালিত হচ্ছে।"
   * **QA Check:** Accurate code-switching phonetics for Python, Playwright, CustomTkinter, and smooth utterance of "স্বয়ংক্রিয়ভাবে" (Sha-yong-kriyo-bha-be).
10. **System Diagnostics:**
    * "গুগলের জেমিনাই লাইভ এপিআই-এর অডিও স্ট্রিমে কোনো লেটেন্সি নেই, এবং ক্রোমাডিবি মেমোরি ঠিকভাবে কানেক্টেড রয়েছে।"
    * **QA Check:** Fluent technical bilingual pronunciation in standard Bangladesh accent.

### Section 5: Emotionally Varied Phrasing & Clarifications (অনুভূতিসম্পন্ন বাক্যালাপ ও স্পষ্টকরণ)
11. **Empathetic Apology (দুঃখ প্রকাশ):**
    * "আন্তরিকভাবে দুঃখিত স্যার, ইন্টারনেট কানেকশন ড্রপ করার কারণে বার্তাটি পৌঁছাতে একটু বেশি সময় লাগছে। আমি পুনরায় চেষ্টা করছি।"
    * **QA Check:** Empathetic, polite emotional expression without flat robotic mono-pitch.
12. **Confidence-based Clarifying Question (সন্দেহ দূরীকরণ):**
    * "স্যার, অডিও সংকেতের কারণে নামটি ঠিক স্পষ্ট বুঝতে পারিনি। আপনি কি রহিম বললেন, নাকি করিম? দয়া করে আরেকবার বলবেন কি?"
    * **QA Check:** Inquisitive rising pitch at question boundaries ("রহিম বললেন, নাকি করিম?").
13. **Destructive Action Confirmation Prompt (সতর্কবার্তা ও সম্মতি):**
    * "সতর্কতা: আপনি ওয়ার্কস্পেসের সমস্ত পুরাতন ডেটা চিরতরে মুছে ফেলার নির্দেশ দিয়েছেন। এটি আর ফিরিয়ে আনা সম্ভব হবে না। আপনি কি সত্যিই এগিয়ে যেতে চান? হ্যাঁ অথবা না বলে নিশ্চিত করুন।"
    * **QA Check:** Serious, calm studio-narrator authority with steady pacing.
14. **Barge-in Acknowledgment (বাধাদান পরবর্তী উত্তর):**
    * "ঠিক আছে স্যার, আগের কাজ থামিয়ে দিলাম। বলুন, এখন কোন বিষয়টি নিয়ে কাজ করব?"
    * **QA Check:** Quick, responsive acoustic adaptation without tone resetting or glitching.
15. **Task Completion Triumph (আনন্দঘন সাফল্য):**
    * "চমৎকার! আমাদের সমস্ত ছয়াব্বিশটি ইউনিট টেস্ট কোনো ত্রুটি ছাড়াই সফলভাবে পাস করেছে এবং প্রজেক্টটি এখন লাইভ রয়েছে।"
    * **QA Check:** Enthusiastic and professional closing tone.
