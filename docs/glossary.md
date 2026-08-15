# Glossary & Translation Style Guide

Single source of truth for terminology. Both Cursor (translation) and Claude
(modernization + gap articles) must follow this file.

## Locked style decisions

| Decision | Choice |
| --- | --- |
| English variant | **American English** (color, behavior, organize) |
| Tone | Friendly, beginner-accessible tutorial voice |
| Person | First-person teaching voice — "let's look at…", "we'll build…" |
| Code identifiers | Never translate — stay exactly as written |
| Angular API terms | Always English — see do-not-translate list below |
| Code in TRANSLATE phase | Left as original-era, marked with legacy comment |
| Social hashtags | Drop entirely — omit from translated output |
| Vietnamese-only links | Keep URL, translate link text, append "(Vietnamese)" |

## Vietnamese → English term map

| Vietnamese | English |
| --- | --- |
| Giới thiệu | Introduction |
| Chuẩn bị | Prerequisites |
| Tiến hành | Getting Started |
| Tổng kết / Kết luận | Summary / Conclusion |
| Ví dụ | Example |
| Lưu ý / Chú ý | Note |
| Cú pháp | Syntax |
| Câu lệnh | Command |
| Ứng dụng | Application / app |
| Thành phần | Component (context-dependent) |
| Bài viết | Article |
| Thực hành | Hands-on / Practical |
| Các bước | Steps |
| Tác giả | Author |
| Có thể bạn đã biết | Did You Know |

## Do-not-translate list

`Angular`, `RxJS`, `Observable`, `Subject`, `NgModule`, `standalone`, `signal`,
`computed`, `effect`, `inject`, `@Input`, `@Output`, `input()`, `output()`,
`ngFor`, `ngIf`, `@if`, `@for`, `@switch`, `@defer`, `ActivatedRoute`, `Router`,
`FormControl`, `FormGroup`, `FormBuilder`, `ngModel`, `ngTemplateOutlet`,
`ng-container`, `ng-template`, `ViewChild`, `ContentChild`, `ViewContainerRef`,
`TemplateRef`, `ElementRef`, `Renderer2`, `ChangeDetectionStrategy`, `OnPush`,
`takeUntilDestroyed`, `toSignal`, `toObservable`, `HttpClient`, `HttpInterceptor`,
`TestBed`, `ComponentFixture`, TailwindCSS, ng-zorro, Akita, NgRx, ngrx, Nx,
and all CLI commands.
