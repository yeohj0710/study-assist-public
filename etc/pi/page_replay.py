"""페이지가 확인된 뒤의 답 재생 순서. 카메라, 문자 인식, GPIO는 호출자가 연결합니다."""


class PageReplay:
    def __init__(self):
        self.answers = {}
        self.confirmed = None
        self.candidate = None
        self.frames = 0
        self.last_frame_at = None
        self.visited = set()
        self.announced = set()
        self.replay = False
        self.visit = 0
        self.active = None
        self.last_finished = None

    def observe(self, book, page, now):
        if book is None or page is None:
            self.candidate = None
            self.frames = 0
            self.last_frame_at = None
            return
        identity = (book, page)
        consecutive = (self.candidate == identity and self.last_frame_at is not None
                       and 0 < now - self.last_frame_at <= 6)
        self.frames = min(self.frames + 1, 2) if consecutive else 1
        self.candidate = identity
        self.last_frame_at = now
        if self.frames == 2 and self.confirmed != identity:
            self.confirmed = identity
            self.replay = identity in self.visited
            self.visited.add(identity)
            self.visit += 1
            self.announced.clear()
            self.last_finished = None

    def save(self, book, pages, question, choice):
        if not pages or not 1 <= question <= 999 or not 1 <= choice <= 5:
            raise ValueError('확정된 쪽과 유효한 문항번호, 보기 번호가 필요합니다.')
        key = (book, min(pages), question)
        self.answers.setdefault(key, (tuple(pages), choice))

    def next_answer(self, now):
        if (self.active is not None or self.frames < 2 or self.confirmed is None
                or self.last_frame_at is None or now - self.last_frame_at > 6):
            return None
        book, page = self.confirmed
        eligible = [key for key, (pages, _) in self.answers.items()
                    if key[0] == book and page in pages]
        remaining = [key for key in eligible if key not in self.announced]
        if not remaining:
            if not eligible or self.last_finished is None or now - self.last_finished < 15:
                return None
            self.replay = True
            self.announced.clear()
            remaining = eligible
        key = min(remaining, key=lambda item: (item[2], item[1])) if self.replay else remaining[0]
        self.active = (self.visit, key)
        return key[2], self.answers[key][1]

    def finished(self, now):
        if self.active is None:
            return
        visit, key = self.active
        self.active = None
        if visit == self.visit:
            self.announced.add(key)
            self.last_finished = now


if __name__ == '__main__':
    player = PageReplay()
    player.observe('예시', 42, 0)
    player.observe('예시', 42, 3)
    player.save('예시', (42,), 18, 4)
    player.save('예시', (42, 43), 17, 3)
    print('첫 방문, 풀이 완료 순서:', player.next_answer(3))
    player.finished(8)
    player.observe('예시', 44, 9)
    player.observe('예시', 44, 12)
    print('다른 페이지:', player.next_answer(12))
    player.observe('예시', 42, 15)
    player.observe('예시', 42, 18)
    print('42쪽 다시 보기, 문항번호 순서:', player.next_answer(18))
