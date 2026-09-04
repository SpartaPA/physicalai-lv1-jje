# 모듈 1 과제 - 배달 로봇 온보딩

## 문제 1. 배달 로봇의 연산 분담과 실시간성 설계

### 전제: 로봇 구성과 계산 기준
- 로봇 구성
	- 2D 라이다(15Hz), RGB 카메라(60fps, 720p), IMU(400Hz), 바퀴 엔코더(2kHz), 모터 드라이버, LTE 모듈(핑: 1~5ms, 업로드 및 다운로드 속도: 95~100Mbps)
- 주행 속도 v = 1.5 m/s, 감속도 a = 2 m/s² 로 가정

**장치별 데이터량 (바퀴 4개 기준)**

| 장치      | 갱신 주기             | 1회 데이터 (가정)                           | 데이터율                      | 비고                              |
| ------- | ----------------- | ------------------------------------- | ------------------------- | ------------------------------- |
| 바퀴 엔코더  | 2kHz<br>(0.5ms)   | 4륜 × 4B 카운터 = 16B                     | 32 KB/s                   | 모터 속도 피드백 및 정밀 출력 제어            |
| IMU     | 400Hz<br>(2.5ms)  | 가속도 3축 + 각속도 3축 × 4B + 타임스탬프 8B = 32B | 12.8 KB/s                 | 자세·오도메트리 융합                     |
| 2D 라이다  | 15Hz<br>(66.7ms)  | 360점 × (거리 4B + 세기 4B) = 2,880B       | 43.2 KB/s (≈ 0.35 Mbps)   | 장애물 감지                          |
| RGB 카메라 | 60fps<br>(16.7ms) | 1280 × 720 × 3B = 2,764,800B ≈ 2.76MB | 165.9 MB/s (≈ 1,327 Mbps) | 보행자 인식 (원시 영상 기준)               |
| LTE 모듈  | —                 | —                                     | 업/다운로드: 95~100 Mbps       | 왕복 지연(RTT, 핑) 1~5ms, 터널·지하에서 끊김 |
 
**계산 참고**
- 2D 라이다 데이터율: 360점 × (거리 4B + 세기 4B) × 15Hz = 43,200 ≈ 43.2KB/s (≈ 0.35Mbps)
- RGB 카메라 데이터율: 1280 × 720 × 3B × 60Hz ≈ 165.9 MB/s 
- 반응 지연: 놓친 센서의 갱신 주기, 진행 거리 = v[m/s] × 지연[s]
	- 2D 라이다 스캔 주기 66.7ms 기준 로봇은 v × 0.0667 ≈ 0.1 m 진행
- 제동 거리: 등감속(a=2m/s²)으로 완전 정지할 때까지 필요한 거리
	- v² / (2a) = 1.5² / (2×2) = 2.25/4 = 0.5625m ≈ 0.56m
- LTE : 업/다운로드 95~100Mbps, 왕복 지연(핑) 1~5ms

---

### 1-1. 연산 분담 배치표
| #   | 작업           | 위치                                | 지연 예산                     | 데이터량                                                 | 근거                                                                                                                                                                                                                                                                                                              |
| --- | ------------ | --------------------------------- | ------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 모터 속도 제어     | 임베디드 (모터 드라이버 MCU)                | ≤ 0.5ms (엔코더 2kHz)        | 엔코더 32KB/s + 명령수                                     | • 제어 주기는 0.5ms인데, LTE RTT는 1~5ms → 그 자체로 제어주기의 2~10배에 달하므로 한 주기 안에 왕복 불가능<br>• 데이터량은 문제가 되지 않지만, 여전히 마감보다 느리고 네트워크는 순간적인 혼잡·지터·단절을 겪을 수 있으므로 결정적 주기의 동작을 보장 못함<br>• Edge 컴퓨터의 범용 OS는 0.5ms 마감을 보장하지 못함<br>• 따라서 MCU의 타이머 인터럽트에서 PID 실행                                                                          |
| 2   | 장애물 감지 (라이다) | Edge AI<br>(온보드 컴퓨터, 비상정지는 임베디드로) | ≤ 66.7ms (스캔 주기 1회 안에 판정) | 43.2KB/s                                             | • 스캔 1회(66.7ms) 놓칠 때마다 로봇은 0.1m 추가 진행<br>• LTE 왕복 지연(1~5ms)만 보면 스캔 주기(66.7ms) 안에 충분히 왕복 가능하지만, 비상정지 같은 안전 임계 기능은 드물게라도 지연이 급증하거나 통신이 끊기는 순간에도 결정적으로 동작해야 함. 그런 순간에 스캔을 한 번이라도 놓치면 0.1m씩 진행거리가 늘어나므로, 평균 지연이 짧다고 해서 클라우드 왕복을 허용할 수 없음.<br>• 따라서 스캔을 통한 장애물 감지는 Edge에서 처리하고, 정지에 대한 최종 판정은 GPIO로 모터 드라이버에 전달되어 처리 |
| 3   | 보행자 인식 (카메라) | Edge AI (GPU 탑재 온보드)              | ≤66.7ms<br>(3~4프레임 안엔 결과) | 원시 165.9MB/s (보드 밖으로 내보내지 않음)<br>출력은 바운딩박스로 수십 B/프레임 | • 원시 영상 1,327Mbps는 LTE 대역폭(95~100Mbps)의 약 13~14배 → 대역폭 자체가 부족해 클라우드로는 성립 불가<br> • 온보드 GPU에서 경량화된 detection 모델로 약 30~40ms 추론 후, 결과만 판단 계층으로 전달                                                                                                                                                                   |
| 4   | 지도 기반 경로 계획  | 클라우드 (전역 경로) + Edge (국소 재계획)      | 1~5s<br>(출발, 재계획 시점에만 수행) | 요청 수백 B, 응답 waypoint 수 KB                            | • 지도 DB는 수 GB이며, 도로 통제, 다른 로봇 위치와 함께 갱신이 이뤄지므로 서버에 둠<br>• 지연에 둔감: 지연이 초 단위로 늘어져도 로봇은 이전 경로를 유지하며 계속 주행할 수 있음<br>• 통신(LTE)이 끊겨도 캐시된 경로로 버틸 수 있고, 국소 회피는 edge에서 15Hz로 돌림                                                                                                                                          |
| 5   | 배달 완료 사진 업로드 | 클라우드                              | 수 초~수 분<br>(비실시간, 재전송 허용) | JPEG 1장 기준 0.5~2 MB, 배달 당 1회                         | • 2MB를 LTE 대역폭(95~100Mbps)으로 전송 시, 약 0.16~0.17s로 매우 여유 있음<br>• 실시간성이 요구되지 않는 이벤트성 전송(배달 완료 시 전송)이라 통신 불량 시에도 큐에 넣고 재시도 가능                                                                                                                                                                                       |
| 6   | 운행 로그 집계     | 클라우드(수집 및 집계), 로그 생성 자체는 Edge     | 분~시간  (배치 단위)             | 원시 로그 수십 KB/s를 local에 쌓음 → 압축 후 배치 업로드, 수십 MB/일      | • 실시간 스트리밍할 이유 X<br>• 여러 로봇의 로그를 모아야 의미가 있음<br>• Wi-Fi 이용 / 유휴 시간 배치 업로드를 통해 LTE 요금 낭비 및 혼잡을 피할 수 있음                                                                                                                                                                                                            |

**배치 판단**
- 임베디드 - 모터 제어
- Edge AI - 장애물 감지, 보행자 인식
- 클라우드 -  경로계획, 사진 업로드, 로그 집계

- **판단 기준**
	1. 지연 예산이 LTE 왕복시간(1~5ms)보다 짧으면 로봇 안에서 처리
	   → 모터 속도 제어 (0.5ms < 1~5ms)
	   → 장애물 감지 (지연만으로는 클라우드로 가능하지만 안전 임계성 때문에 로봇 안에서 처리)
	2. 데이터량이 LTE 대역폭(95~100Mbps)을 넘으면 로봇 안에서 처리 
	   → 보행자 인식(원시영상 1,327Mbps)은 LTE 대역폭을 초과해 Edge AI 처리
	   → 지도 기반 경로 계획, 배달 완료 사진 업로드, 운행 로그 집계는 수 KB~MB 수준이라 클라우드 처리 가능

---

### 1-2. 카메라 원시 영상 전송량과 LTE 비교

```text
1프레임 크기 = 1280 × 720 × 3B = 2,764,800B ≈ 2.76MB
초당 전송량 = 2.76MB × 60fps ≈ 165.9MB/s ≈ 1,327Mbps ≈ 1.33 Gbps
```

**카메라 원시 영상 전송량 = 165.9 MB/s (≈ 1,327 Mbps) — LTE 대비 판단: 성립하지 않음 (LTE 업링크 대역폭 95~100Mbps의 약 13~14배이기 때문)**

| 항목        | 값          | 원시 영상 대비   |
| --------- | ---------- | ---------- |
| 필요 대역폭    | 1,327 Mbps | -          |
| LTE 실측 상한 | 100 Mbps   | 약 13.3배 부족 |
| LTE 실측 하한 | 95 Mbps    | 약 14.0배 부족 |

 가장 좋은 시나리오(100Mbps)를 적용해도 13.3배가 부족함
 → 원시 영상을 클라우드로 계속 전송하는 설계는 어떤 조건에서도 성립하지 않음

- **처리량 관점**: 100Mbps 링크로는 프레임 1장(2.76MB≈22.1Mb) 전송에 약 0.22초가 걸려 사실상 초당 약 4.5프레임 수준까지만 가능 → 정보가 쌓이면 지연은 계속해서 커짐 
- **지연 관점**: 대역폭이 충분하다해도, 프레임 1장 전송에만 100Mbps 기준 약 221ms가 걸려(처리량 관점 계산 참고) 이미 보행자 인식 지연예산(66.7ms)의 3배가 넘음 → 대역폭 부족이 지연 예산 초과로 이어지는 근본적인 병목
- **총량·비용 관점**: 하루 8시간 운행 기준 데이터량이 165.9MB/s × 28,800s ≈ 약 4.78TB/일 정도임, 따라서 이 정도 총량을 상시 스트리밍하는 것은 통신 요금·안정성 측면에서 비효율적 (감당 X)

이러한 이유로 추론은 Edge에서 수행하고, 결과값만 클라우드로 전송하는 구조가 합리적

---
### 1-3. 인지 · 판단 · 제어 계층 매핑과 주기표

**계층 매핑**

| 계층     | 작업           | 갱신 주기                                                 | 실행 위치                                          | 입력 → 출력                                                                                 |
| ------ | ------------ | ----------------------------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------- |
| 인지     | 장애물 감지       | 15Hz                                                  | Edge (+MCU 비상정지)                               | 라이다 스캔 → 장애물 점군·최근접 거리                                                                  |
| 인지     | 보행자 인식       | 60Hz 입력 / 10~30Hz 출력                                  | Edge (GPU)                                     | 카메라 프레임 → 보행자 바운딩박스·거리                                                                  |
| 판단     | 지도 기반 경로 계획  | 1) 전역 경로 - 이벤트 기반 (비주기)<br>2) 국소 경로·속도결정 (재계획) - 15Hz | 1) 전역 경로 - 클라우드<br>2) 국소 경로·속도 결정 (재계획) - Edge | 1) 전역 경로 - 출발·목적지·지도 → waypoint 열<br>2) 국소 경로·속도 결정 - waypoint + 장애물 + 보행자 → 목표 선속도·각속도 |
| 제어     | 모터 속도 제어     | 2kHz                                                  | 임베디드                                           | 목표 속도 vs 엔코더 → PWM 듀티                                                                   |
| (비실시간) | 배달 완료 사진 업로드 | 이벤트 기반 (배달 완료 시)                                      | 클라우드                                           | JPEG → 저장·알림                                                                            |
| (비실시간) | 운행 로그 집계     | 배치 (1/분~1/시간)                                         | 클라우드                                           | 로그 파일 → 통계·대시보드                                                                         |

**멀티레이트 데이터 흐름**

<img src="./images/multirate.png" width="700">
 
- 빠른 루프가 느린 루프의 최신 값을 읽고, 없으면 이전 값을 유지
- 느린 루프가 빠른 루프를 막지 않도록 각 계층을 분리하는 것
- 각 데이터에 타임스탬프를 붙여 판단 계층이 이를 인식해 오도메트리로 보정할 수 있게 함
- 라이다 비상 정지는 판단 계층을 거치지 않고 모터드라이버로 직결해, 상위 계층이 멈춰도 정지가 보장되도록 함

---

### 1-4. Hard / Firm / Soft 실시간 분류표

| 작업           | 분류   | 마감                   | 마감 초과 결과                                                                                      | 근거                               |
| ------------ | ---- | -------------------- | --------------------------------------------------------------------------------------------- | -------------------------------- |
| 모터 속도 제어     | Hard | 0.5ms                | PID가 잘못된 dt로 적분·미분해 출력이 튀고, 연속으로 놓치면 제어가 발산하여 바퀴 속도가 폭주 / 좌우 바퀴 속도가 어긋나 궤적을 이탈하거나, 경사로에서 미끄러짐 | 한 번의 마감 초과가 곧 물리적 사고로 이어짐, 치명적임  |
| 장애물 감지       | Hard | 66.7ms<br>(스캔 1회)    | 스캔 하나를 놓칠 때마다 로봇이 0.1m를 예상보다 더 진행하고, 여러 번 놓치면 제동거리(0.56m 기준) 여유가 사라져 사람 or 물체와 충돌 가능          | 안전 기능, 마감 초과 시 충돌 확률이 직접적으로 증가   |
| 보행자 인식       | Firm | 66.7ms<br>(≈ 3~4프레임) | 늦게 나온 인식 결과는 폐기하고 다음 프레임을 쓰면 됨<br>가끔 놓쳐도 라이다 비상정지가 안전을 보장하므로 사고로 직결되지는 않음                     | 늦은 결과는 가치가 없지만, 놓치더라도 시스템 실패는 아님 |
| 지도 기반 경로 계획  | Soft | 1~5s                 | 응답이 늦어지면, 이전 경로로 계속 주행하거나 잠시 대기<br>늦어질수록 배달 시간이 늘지만, 늦은 경로도 쓰는 데 지장 없음                        | 늦으면 가치가 점차 감소할 뿐, 0이 아님          |
| 배달 완료 사진 업로드 | Soft | 수 분                  | 고객 알림이 늦어질 뿐, 실패해도 재시도 하면 됨                                                                   | 재시도가 가능, 마감 느슨함                  |
| 운행 로그 집계     | Soft | 시간 단위                | 대시보드가 늦게 갱신될 뿐                                                                                | 배치 작업, 마감 없음에 가까움                |
 
**분류 기준**
- Hard: 마감을 넘기는 순간 가치가 음수, 치명적인 물리적 사고로 이어짐
- Firm: 마감을 넘긴 결과는 가치가 0이 되어 폐기, 사고는 아님
- Soft: 마감을 넘겨도 가치가 점진적으로 하락할 뿐
 
> **Hard 항목의 마감 초과 결과**
> • **모터 속도 제어**: 0.5ms의 마감을 놓치면 PID 출력이 튀어 바퀴 속도가 폭주하거나 좌우 바퀴 속도가 어긋나 로봇이 궤적을 이탈하고, 경사로에서는 미끄러져 치명적인 물리적 사고로 이어질 수 있음
> • **장애물 감지**: 66.7ms의 마감을 놓칠 때 마다 로봇이 0.1m 더 진행하여 여러 번 누적해서 놓치면 제동 거리 여유가 사라지고, 사람이나 장애물과 충돌할 수 있음


---
 
### 1-5. 주기 · 지연 · 지터 구분

- **주기(period)**: 작업이 얼마나 자주 반복되는가
	 ex) 배달로봇 기준: 모터 속도 제어 루프는 엔코더를 0.5ms마다 읽고 PWM을 갱신하므로 주기가 0.5ms(2 kHz)이고, 라이다 장애물 감지는 66.7ms(15Hz)임
- **지연(latency)**: 입력이 들어와서 출력이 나올 때 까지 걸리는 시간
	  ex) 배달로봇 기준: 보행자가 카메라에 잡힌 순간부터 판단 계층이 결과를 받기까지 약 61.7ms가 걸림 (바운딩박스 결과를 받기까지 캡쳐 16.7ms, GPU 추론 40ms + 전달 5ms ≈ 61.7ms) → 그동안 로봇은 9.3cm를 진행함
- **지터(jitter)**: 주기 or 지연이 얼마나 들쭉날쭉한가(편차)
	  ex) 배달로봇 기준: 0.5ms 주기여야 할 제어 루프가 OS 스케줄링 때문에 실제로는 0.35~0.65ms 사이로 실행되면 지터가 ±0.15 ms 이고, 이 편차가 PID 의 dt 를 오염시킴
	  → Hard 작업은 평균 지연보다 최악인 지터를 먼저 줄여야함

+) 참고: 지연은 평균이 아닌 최악을 기준으로 계산해야함.
 
---

## 문제 2. 원격 접속(SSH)과 센서 장치 경로 고정

### 2-1. 접속 대상 선택 및 원격 세션 확인

**접속 대상 선택**
- local host 선택
- 접속 명령

```bash
ssh pa34@localhost
```

→ 들어갈 때마다 비밀번호를 쳐야함

**SSH 서버 작동 확인**
- `systemctl status ssh`를 통해 SSH 서버가 active한지 확인
```bash
systemctl status ssh
```

- 실행 결과: active (running)이 뜨는 것을 확인
```bash
● ssh.service - OpenBSD Secure Shell server
     Loaded: loaded (/lib/systemd/system/ssh.service; enabled; vendor preset: enabled)
     Active: active (running) since Sun 2026-08-30 13:56:01 KST; 8h ago
       Docs: man:sshd(8)
             man:sshd_config(5)
    Process: 1032 ExecStartPre=/usr/sbin/sshd -t (code=exited, status=0/SUCCESS)
   Main PID: 1059 (sshd)
      Tasks: 1 (limit: 37554)
     Memory: 3.0M
        CPU: 16ms
     CGroup: /system.slice/ssh.service
             └─1059 "sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups"

Aug 30 13:56:01 pa34-Legion-Pro-5-16IAX10 systemd[1]: Starting OpenBSD Secure Shell server...
Aug 30 13:56:01 pa34-Legion-Pro-5-16IAX10 sshd[1059]: Server listening on 0.0.0.0 port 22.
Aug 30 13:56:01 pa34-Legion-Pro-5-16IAX10 sshd[1059]: Server listening on :: port 22.
Aug 30 13:56:01 pa34-Legion-Pro-5-16IAX10 systemd[1]: Started OpenBSD Secure Shell server.
```
<img src="./images/systemctl.png" width="800">


- 서버가 22번 포트로 듣고 있는지 확인
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~$ ss -tlnp | grep :22
LISTEN 0      128          0.0.0.0:22        0.0.0.0:*          
LISTEN 0      128             [::]:22           [::]:* 
```


**진짜 원격 세션인지 확인**

1) 확인 명령
```bash
ssh pa34@localhost
who
echo $SSH_CONNECTION
```

2) 실행 결과
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~$ ssh pa34@localhost
Welcome to Ubuntu 22.04.5 LTS (GNU/Linux 6.8.0-138-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

Expanded Security Maintenance for Applications is not enabled.

202 updates can be applied immediately.
To see these additional updates run: apt list --upgradable

144 additional security updates can be applied with ESM Apps.
Learn more about enabling ESM Apps service at https://ubuntu.com/esm

Last login: Fri Aug 28 14:27:31 2026 from 127.0.0.1
```

```bash
pa34@pa34-Legion-Pro-5-16IAX10:~$ who
pa34     :0           2026-08-30 13:56 (:0)
pa34     pts/1        2026-08-30 22:12 (127.0.0.1)
```
- `who`출력: `pts/0`세션의 출발지가  127.0. 0.1로 표시되어, 물리 콘솔 세션인 `:0`과 달리 이 세션이 sshd를 통해 네트워크로 접속된 세션임을 확인

```bash
pa34@pa34-Legion-Pro-5-16IAX10:~$ echo $SSH_CONNECTION
127.0.0.1 33724 127.0.0.1 22
```
- `echo $SSH_CONNECTION` 출력: `[클라이언트 IP] [클라이언트 포트] [서버 IP] [서버 포트]`


---
 
### 2-2. 무비밀번호 접속과 키 등록

- 무비밀번호 접속을 위해 키 쌍을 생성해 등록해줘야 함 (키 기반 인증)
```bash
ssh-keygen -t ed25519
cat .ssh/id_ed25519
ssh-copy-id pa34@localhost
```
- `ssh-keygen -t ed25519`
	- ED25519 알고리즘으로 비대칭 키 쌍(개인키, 공개키)을 생성
	- 명령어를 실행하고 나면 `id_ed25519`(개인키)와 `id_ed25519.pub`(공개키) 두 파일이 생성됨
- `cat .ssh/id_ed25519`
	- 생성된 개인키 파일의 원문을 그대로 확인할 수 있는 명령
	- 해당 파일은 OpenSSH 전용 형식 (`-----BEGIN OPENSSH PRIVATE KEY-----`~`-----END OPENSSH PRIVATE KEY-----)
- `ssh-copy-id pa34@localhost`
	- 로컬에서 생성한 공개키(`id_ed25519.pub`)만 접속하고자 하는 계정(`pa34@localhost`)에 접속해 원격서버의 `~/.ssh/authorized_keys` 파일 끝에 공개키를 추가하는 명령
	- 명령어 실행 후, 비밀번호 없이 접속 가능
	- 이 과정에서 네터워크를 통해 **서버로 전달, 저장되는 것은 공개키뿐이며 개인키는 로컬 머신을 벗어나지 않음**
 
- 실행 결과: password 입력 없이도 바로 접속할 수 있음을 확인 ![wo_password](./images/ssh_wo_password.gif)
 

>**이 방식이 안전한 이유**⭐ 
>• 서버에는 공개키가 등록되며, 개인키는 클라이언트(로컬)에만 남음
>• 공개키로부터 개인키를 역산하는 것은 사실상 불가능하므로, 공개키가 유출되어도 개인키를 복원할 수 없음
>• 인증 과정에서 클라이언트는 개인키로 서명하고 서버는 공개키로 검증하므로, 개인키 자체가 네트워크를 통해 전송되지 않음
>• 비밀번호를 직접 전송하지 않아 스니핑·무차별 대입·재전송 공격에 대한 위험이 낮고, 자동화 환경에서도 안전하게 사용 가능
 
 
---
 
### 2-3. 원격 단일 명령 실행과 scp 전송 출력

**헤드리스 운용에서 자주쓰는 2가지**
1) **원격 단일 명령 실행**
	- 그냥 ssh 접속을 하며 셸이 열리고, 터미널에서 여러 명령을 쳐가면서 작업하다 `exit`으로 나옴
	- 단일  명령 실행은 원격 셸을 띄우는 대신, 곧바로 하나의 명령만 원격에서 실행해 로컬 터미널로 출력 결과를 보인 후 자동으로 연결을 끊음

2) **scp(secure copy) 전송**
	- SSH와 같은 암호화 채널을 써 로컬과 원격 사이에 파일을 복사하는 명령


**원격 단일 명령 실행**
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~$ ssh pa34@localhost 'uname -a'
Linux pa34-Legion-Pro-5-16IAX10 6.8.0-138-generic #138~22.04.1-Ubuntu SMP PREEMPT_DYNAMIC Fri Aug  7 13:43:15 UTC  x86_64 x86_64 x86_64 GNU/Linux
```
- localhost에 접속해 `uname -a` 라는 단일 명령을 수행하고 연결 끊음


**scp 파일 전송**
- 기본 경로에 scp_test.txt 파일을 생성함 (vi 이용 - 내용 작성후 저장함)
- scp를 통해 파일을 전송할 때, 경로가 겹치지 않도록 목적지 폴더로 scp_test 폴더 생성
- scp 후 scp_test 폴더에 scp_test.txt가 있는지 확인

```bash
vi scp_test.txt
mkdir -p ~/scp_test
ls ~/scp_test            # 전송 전이므로 비어있음
scp scp_test.txt pa34@localhost:~/scp_test/        # scp로 파일 전송
ls ~/scp_test            # 전송 후이므로 scp_test.txt가 있음
```

![scp 파일 전송](./images/scp_example.png)
 
 
---
 
### 2-4. 가상 센서(loop 장치) 설정과 udevadm을 이용한 구분 속성 확인

**시리얼 장치 파일 종류 및 소유 그룹 확인 (`/dev/tty*`)**

<img src="./images/tty1.png" width="300"> <img src="./images/tty2.png" width="300">

< 실제 터미널 결과에서 가져온 일부 - 위의 이미지 참조 >
```
crw-rw-rw- 1 root tty     5,  0 Aug 28 08:47 /dev/tty
crw--w---- 1 root tty     4,  0 Aug 28 08:47 /dev/tty0
crw-rw---- 1 root dialout 4, 64 Aug 28 08:47 /dev/ttyS0
```
- 읽는 법: `파일 종류(1글자)` `소유자 권한(3글자)` `그룹 권한(3글자)` `기타 권한(3글자)`
- `/dev/tty`
	- 파일 종류 문자 `c`(문자 장치, character device)
	- 권한: `rw-rw-rw-`는 소유자(root), 그룹(tty), 기타 사용자 모두에게 읽기, 쓰기를 허용
- `/dev/tty0`
	- 파일 종류 문자 `c`
	- 권한: `rw--w----`는 소유자(root)만 읽기, 쓰기가 가능하고, 그룹(tty)은 쓰기만 가능, 기타 사용자는 접근 권한이 없음
- `/dev/ttyS0`
	- 파일 종류 문자 `c`
	- 권한: `rw-rw----`는 소유자(root)와 그룹(dialout) 모두 읽기, 쓰기가 가능하고 기타 사용자는 접근 권한이 없음
 
 
**가상센서(loop 장치) 부착**
- lidar와 imu 가상 센서 부착
```bash
mkdir -p ~/fake_sensors && cd ~/fake_sensors
truncate -s 16M lidar.img
truncate -s 24M imu.img
sudo losetup -f --show lidar.img    # /dev/loop17
sudo losetup -f --show imu.img    # /dev/loop18
```
- 출력 결과: lidar는 /dev/loop17, imu는 /dev/loop18

 
**장치 식별 속성(`backing_file`)과 udev 규칙(`rules`)의 차이**
- `backing_file`(장치 속성, Attribute): 가상 루프 장치(/dev/loopN)에 매핑되어 **실제 데이터의 입출력을 처리하는 원본 이미지 파일**이자, 커널이 관리하는 **해당 파일의 절대 경로 상태 정보**
- `rules` (udev 규칙, Rule): 특정 속성을 가진 장치가 인식되었을 때 시스템이 수행할 동작을 정의한 조건문(If-Then) 파일
- 차이 - `backing_file`은 장치를 식별하기 위한 '<u>판단 기준 (정보)</u>'이며, `rules`는 그 기준을 바탕으로 고정이름(e.g. `/dev/lidar`)을 부여하는 '<u>행동 지침 (명령)</u>'


**장치 비교 속성 분석 및 검토**
- `udevadm info --attribute-walk /dev/loopN` 로 각 속성 조사
- loop 17 속성 결과 (`udevadm info --attribute-walk /dev/loop17`)
<img src="./images/loop17_1.png" width="300"> <img src="./images/loop17_2.png" width="300">

- loop 18 속성 결과 (`udevadm info --attribute-walk /dev/loop18`)
<img src="./images/loop18_1.png" width="300"> <img src="./images/loop18_2.png" width="300">

- 두 장치 속성 비교 결과 달랐던 부분: `ATTR{diskseq}`, `ATTR{stat}` 
```bash
# /dev/loop17 - ~/fake_sensors/lidar.img
ATTR{diskseq}=="39"
ATTR{size}=="32768"
ATTR{stat}=="      79        0     1372        0        0        0        0        0        0        1        0        0        0        0        0        0        0"

# /dev/loop18 - ~/fake_sensors/imu.img
ATTR{diskseq}=="41"
ATTR{size}=="49152"
ATTR{stat}=="      68        0     1344        1        0        0        0        0        0        2        1        0        0        0        0        0        0"
```
- `ATTR{diskseq}`(디스크 시퀀스 번호): 커널이 블록 장치를 새로 생성할 때마다 순차적으로 부여하는 일련번호. **재연결 시마다 값이 바뀜**
- `ATTR{size}`(섹터 수): lidar `32768`섹터×512B = 16,777,216B = 16MB, imu `49152`섹터×512B = 25,165,824B = 24MB - `truncate -s 16M/24M`로 지정한 파일 크기와 정확히 일치. 두 장치를 구분하고, 재연결해도 값이 바뀌지 않음 → **backing_file 외에 추가로 쓸 수 있는 구분 속성**
- `ATTR{stat}`(입출력 통계): 읽기, 쓰기 요청 횟수, 처리한 섹터 수 등 실시간 I/O 누적 카운터. 그 장치에 어떤 입출력이 발생했는냐에 따라 **값이 계속 변경됨.**
 
**참고)** 커널은 속성 X - `kernel`은 `udevadm info` 결과 상단에 표시되는 시스템 매칭 환경 정보일 뿐, 개별 센서 장치를 구분짓는 '장치 속성(attribute)'가 아님
 
 
> **속성 확인 시 `loop/backing_file` 확인 불가**
> - `udevadm info --attribute-walk`는 값이 `/`로 시작하는 속성(경로 형태)을 의도적으로 출력에서 제외하도록 구현되어 있어, 절대 경로 값을 갖는 `loop/backing_file`은 이 목록에 나타나지 않음[^1]
> - 대신 `cat /sys/class/block/loopN/loop/backing_file`로 sysfs 파일을 직접 조회해 값 확인 가능


**backing_file 조회 결과** ⭐ 
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~$ cat /sys/class/block/loop17/loop/backing_file
/home/pa34/fake_sensors/lidar.img
pa34@pa34-Legion-Pro-5-16IAX10:~$ cat /sys/class/block/loop18/loop/backing_file
/home/pa34/fake_sensors/imu.img
```
- `cat /sys/class/block/loop17/loop/backing_file` 결과: `/home/pa34/fake_sensors/lidar.img`
-  `cat /sys/class/block/loop18/loop/backing_file` 결과: `/home/pa34/fake_sensors/imu.img`
 
→  **두 장치에서 차이나는 속성이자, 변하지 않는 값 (장치를 식별 할 수 있는 속성): ATTR{size}, backing_file에 존재하는 경로**

---

### 2-5. udev 규칙 작성 및 규칙 키 설명

**udev 규칙 작성**
- `/etc/udev/rules.d/99-robot-sensor.rules` 작성
-  절대 경로가 loop/backing_file이라는 속성을 통해 반영, 추가적인 보조식별자로 size 속성 이용
 ```bash
 # 99-robot-sensor.rules (for delivery robot)
# 구분 속성: backing_file(/sys/block/loopN/loop/backing_file)에 적힌 속성 = losetup으로 붙인 이미지 파일 경로

# lidar: /dev/loop17 -> /dev/robot_lidar
SUBSYSTEM=="block", KERNEL=="loop*", ATTR{loop/backing_file}=="/home/pa34/fake_sensors/lidar.img", ATTR{size}=="32768", SYMLINK+="robot_lidar", MODE="0660", GROUP="dialout"

# imu: /dev/loop18 -> /dev/robot_imu
SUBSYSTEM=="block", KERNEL=="loop*", ATTR{loop/backing_file}=="/home/pa34/fake_sensors/imu.img", ATTR{size}=="49152", SYMLINK+="robot_imu", MODE="0660", GROUP="dialout"
 ```

 
**규칙 키 설명**

| 키           | 의미                                                                  | 위 케이스의 경우                                                                                                         |
| ----------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `SUBSYSTEM` | 장치가 속한 커널 서브시스템 매칭<br>(`block`: 블록 장치, `tty`: 터미널, `usb`: USB 버스 등) | `SUBSYSTEM=='block`으로 loop 장치가 블록 장치 서브시스템에 속한 것만 이 규칙 대상으로 좁힘                                                    |
| `KERNEL`    | 커널이 붙인 이름을 패턴 매칭<br>(`*`는 임의 문자열)                                   | `KERNEL=="loop*"`로 loop0, loop17 등 loop로 시작하는 모든 이름을 후보로 넓게 잡음                                                    |
| `ATTR{...}` | sysfs 속성값 매칭                                                        | `ATTR{loop/backing_file}=="파일경로"`로, 이 loop 장치가 감싸고 있는 원본 파일 경로 작성하여 매칭 - 각 센서를 구분할 수 있는 <u>변하지 않는 속성 값</u>을 작성해야함 |
| `SYMLINK+=` | `/dev/`아래에 원래 장치명은 그대로 둔 채, 추가로 접근할 수 있는 심볼릭 링크 이름을 하나 더 만들어줌.      | `SYMLINK+=robot_lidar`와 같이 작성하여 접근할 수 있는 심볼릭 링크 이름을 생성                                                            |
| `MODE`      | udev가 장치 파일을 만들 때 적용할 권한 (8진수, `chmod`와 같은 표기)                      | `MODE=0660`으로 소유자와 그룹만 읽기, 쓰기 가능하도록 설정, 기타 사용자는 접근 X                                                              |
| `GROUP`     | 장치 파일의 소유 그룹 지정                                                     | `GROUP="dialout"`으로 지정해, `dialout` 그룹에 속한 사용자는 `/dev/robot_lidar`와 `/dev/robot_imu`에 sudo 없이 접근 가능                |
 
- 참고: `==`는 매칭 조건 (비교), `=`/`+=`는 값 대입 (할당)
 
 
---

### 2-6. udev 규칙 재적용 및 순서 변경 후 재연결

**udev 규칙 재적용**
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/fake_sensors$ sudo udevadm control --reload-rules
pa34@pa34-Legion-Pro-5-16IAX10:~/fake_sensors$ sudo udevadm trigger
pa34@pa34-Legion-Pro-5-16IAX10:~/fake_sensors$ ls -l /dev/robot_*
lrwxrwxrwx 1 root root 6 Aug 30 22:30 /dev/robot_imu -> loop18
lrwxrwxrwx 1 root root 6 Aug 30 22:30 /dev/robot_lidar -> loop17
```
- `sudo udevadm control --reload-rules`를 이용해 규칙 업데이트
- `sudo udevadm trigger`: 현재 시스템에 연결된 장치들에 이벤트를 강제로 발생시켜, udev 규칙을 즉시 다시 적용하도록 만드는 명령어
	- 필요한 이유: `sudo udevadm control --reload-rules`는 수정된 규칙 파일을 udev 데몬의 메모리에 loading(새로고침)만 함 (실제 장치에는 아직 아무 일도 안 일어남) →`sudo udevadm trigger`를 통해 이미 꽂혀있는 장치들에게 지금 막 컴퓨터에 새로 꽂혔다는 거짓 커널 신호(uevent)를 강제로 보냄으로써 변경된 udev 규칙을 반영하도록 함

**장치 해제**
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/fake_sensors$ sudo losetup -d /dev/loop17 /dev/loop18
```

 
**순서 변경 후 재연결 확인**
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/fake_sensors$ sudo losetup -f --show imu.img
/dev/loop17
pa34@pa34-Legion-Pro-5-16IAX10:~/fake_sensors$ sudo losetup -f --show lidar.img
/dev/loop18
pa34@pa34-Legion-Pro-5-16IAX10:~/fake_sensors$ ls -l /dev/robot_*
lrwxrwxrwx 1 root root 6 Aug 30 22:31 /dev/robot_imu -> loop17
lrwxrwxrwx 1 root root 6 Aug 30 22:31 /dev/robot_lidar -> loop18
```
- 순서를 변경해 연결하자 기존(lidar - `/dev/loop17`, imu - `/dev/loop18`)에서 **imu - `/dev/loop17`, lidar - `/dev/loop18`로 변경됨**
- `ls -l /dev/robot_*` 출력 결과
	- `/dev/robot_lidar`는 `/dev/loop18`을, `/dev/robot_imu`는 `/dev/loop17`을 각각 가리키도록 자동 갱신됨


> **결론**
> 장치가 시스템에 연결되는 순서나 loop 번호가 바뀌더라도, udev 규칙이 고유 식별자(loop/backing_file)를 기준으로 장치를 탐색하므로 고정된 심볼릭 링크(`/dev/robot_lidar`, `/dev/robot_imu`)는 항상 올바른 장치를 가리킨다는 것을 확인할 수 있음


---

### 2-7. 실제 USB 센서용 규칙과 구분 근거

**실제 USB 센서용 규칙**

- 규칙 초안
	- 같은 규칙을 실제 USB 시리얼 센서(라이다 idVendor `10c4`/idProduct `ea60`, IMU `10c4`/`ea70`)에 적용한다면
```bash
# robot_lidar
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="robot_lidar", MODE="0660", GROUP="dialout"

# robot_imu
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea70", SYMLINK+="robot_imu", MODE="0660", GROUP="dialout"
```

- 변경할 키: `SUBSYSTEM`을 `tty`로 변경, `KERNEL` 사용 X, 구분 속성 `ATTR{loop/backing_file}`을 `ATTRS{idVendor}`, `ATTRS{idProduct}`로 변경

**현재 상황**: idVendor가 같고 idProduct만 다른 상황
- `idVendor`는 두 장치가 동일하므로 그것만으로 구분이 X
- `idProduct`는 제조사가 모델별로 다르게 부여하는 값이므로, lidar와 IMU 값이 다름
	- 이를 **ATTRS에서 구별되는 속성 값으로 반영**
	  (`idVendor`와 `idProduct`는 시리얼 장치 노드(`/dev/ttyUSB0`) 자신의 속성이 아니라 상위(parent) USB 장치의 속성이므로, 장치 자신만 보는 `ATTR{}`이 아니라 부모 장치 체인까지 올라가면서 찾는 `ATTRS{}`를 써야함)
	- `idVendor`와 `idProduct`속성 두 조건을 동시에 매칭시키면 두 장치를 구분 가능


> **완전히 같은 모델의 센서가 여러대 꽂히는 경우**
> `idVendor`, `idProduct`까지 전부 동일한 여러 개의 센서가 꽂히는 경우, 이 두 키만으로는 구분이 X
> → 따라서, `ATTRS{serial}` (장치 고유 시리얼) 또는 USB 포트 위치 기반의 `KERNELS`/`ENV{ID_PATH}`를 보조 조건으로 추가해야 함


---

## 문제 3. 팀 저장소 협업 - 브랜치·충돌 해결·PR 리뷰

### 3-1. 저장소 생성 및 첫 커밋

**저장소 생성**
- 저장소 URL: https://github.com/SpartaPA/assignment1_jje
- PR URL: https://github.com/SpartaPA/assignment1_jje/pull/2

**README.md 작성 & 첫 커밋 push**
- 생성한 저장소를 local로 git clone
- README.md 파일에 배달 로봇 센서 사양(센서 목록 및 주기)를 작성하고 첫 커밋 push
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git add README.md
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git commit -m "docs: 배달 로봇 센서 사양(센서 목록 및 주기) 작성"
[main (최상위-커밋) dd047c7] docs: 배달 로봇 센서 사양(센서 목록 및 주기) 작성
 1 file changed, 17 insertions(+)
 create mode 100644 README.md
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git push origin main
오브젝트 나열하는 중: 3, 완료.
오브젝트 개수 세는 중: 100% (3/3), 완료.
Delta compression using up to 24 threads
오브젝트 압축하는 중: 100% (2/2), 완료.
오브젝트 쓰는 중: 100% (3/3), 1.22 KiB | 1.22 MiB/s, 완료.
Total 3 (delta 0), reused 0 (delta 0), pack-reused 0
To github.com:SpartaPA/assignment1_jje.git
 * [new branch]      main -> main
```


---

### 3-2. PR 리뷰 코멘트와 반영 커밋

1) `feature/compute-layout` 브랜치 - 문제 1 연산 분담 설계 commit

- 브랜치 생성: `git switch -c feature/compute-layout`
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git switch -c feature/compute-layout
새로 만든 'feature/compute-layout' 브랜치로 전환합니다
```

-  `compute_layout.md` 파일 commit
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git add compute_layout.md
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git commit -m "docs: 연산 분담 배치 설계 문서 추가"
[feature/compute-layout adf80d2] docs: 연산 분담 배치 설계 문서 추가
 1 file changed, 18 insertions(+)
 create mode 100644 compute_layout.md
```

- push
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git push -u origin feature/compute-layout
오브젝트 나열하는 중: 4, 완료.
오브젝트 개수 세는 중: 100% (4/4), 완료.
Delta compression using up to 24 threads
오브젝트 압축하는 중: 100% (3/3), 완료.
오브젝트 쓰는 중: 100% (3/3), 2.17 KiB | 2.17 MiB/s, 완료.
Total 3 (delta 0), reused 0 (delta 0), pack-reused 0
remote: 
remote: Create a pull request for 'feature/compute-layout' on GitHub by visiting:
remote:      https://github.com/SpartaPA/assignment1_jje/pull/new/feature/compute-layout
remote: 
To github.com:SpartaPA/assignment1_jje.git
* [new branch]      feature/compute-layout -> feature/compute-layout
'feature/compute-layout' 브랜치가 리모트의 'feature/compute-layout' 브랜치를 ('origin'에서) 따라가도록 설정되었습니다
```

2) `feature/udev-rules` 브랜치 - 문제 2 규칙(rules) 파일 + 설명표 커밋

- 브랜치 생성
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git switch -c feature/udev-rules
새로 만든 'feature/udev-rules' 브랜치로 전환합니다
```

- `99-robot-sensor.rules`, `udev_rules_table.md` 파일 commit
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git add 99-robot-sensor.rules udev_rules_table.md
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git commit -m "feat: udev 규칙 파일 및 키 설명표 추가"
[feature/udev-rules dea14a8] feat: udev 규칙 파일 및 키 설명표 추가
 2 files changed, 22 insertions(+)
 create mode 100644 99-robot-sensor.rules
 create mode 100644 udev_rules_table.md
```

- push
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git push -u origin feature/udev-rules
오브젝트 나열하는 중: 5, 완료.
오브젝트 개수 세는 중: 100% (5/5), 완료.
Delta compression using up to 24 threads
오브젝트 압축하는 중: 100% (4/4), 완료.
오브젝트 쓰는 중: 100% (4/4), 1.64 KiB | 1.64 MiB/s, 완료.
Total 4 (delta 0), reused 0 (delta 0), pack-reused 0
remote: 
remote: Create a pull request for 'feature/udev-rules' on GitHub by visiting:
remote:      https://github.com/SpartaPA/assignment1_jje/pull/new/feature/udev-rules
remote: 
To github.com:SpartaPA/assignment1_jje.git
 * [new branch]      feature/udev-rules -> feature/udev-rules
'feature/udev-rules' 브랜치가 리모트의 'feature/udev-rules' 브랜치를 ('origin'에서) 따라가도록 설정되었습니다.
```


**PR 열기**
- `feature/udev-rules` branch에서 Pull Request

**PR 리뷰 및 반영**
- PR 리뷰 ![PR 리뷰](./images/review.png)
	- `/home/pa34/fake_sensors/lidar.img`와 같이 하드코딩 되어있는 경로에 대해 지적받음

- 리뷰 반영 
	- 개인 환경에 맞게 수정이 필요함을 주석으로 명시
	- 수정 후 파일 push
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git add 99-robot-sensor.rules

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git commit -m "fix: 리뷰 반영 - 경로 변경 필요 주석 추 가"
[feature/udev-rules 628bd26] fix: 리뷰 반영 - 경로 변경 필요 주석 추가
 1 file changed, 1 insertion(+)
 
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git push
오브젝트 나열하는 중: 5, 완료.
오브젝트 개수 세는 중: 100% (5/5), 완료.
Delta compression using up to 24 threads
오브젝트 압축하는 중: 100% (3/3), 완료.
오브젝트 쓰는 중: 100% (3/3), 452 바이트 | 452.00 KiB/s, 완료.
Total 3 (delta 2), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (2/2), completed with 2 local objects.
To github.com:SpartaPA/assignment1_jje.git
   72488b5..628bd26  feature/udev-rules -> feature/udev-rules

```

![리뷰 반영](./images/review_fix.png)

- branch merge ![merge](./images/merge.png)


---

### 3-3. Conflict

충돌을 만들 파일: README.md 파일 (라이다 주기 1. 15Hz 수정, 2. 20Hz 수정)

**`branch-a` 생성 및 README 수정**
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git switch -c branch-a
새로 만든 'branch-a' 브랜치로 전환합니다

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git add README.md

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git commit -m "update:lidar 주기 15Hz로 수정"
[branch-a 8e1a48e] update:lidar 주기 15Hz로 수정
 1 file changed, 1 insertion(+), 1 deletion(-)

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git push -u origin branch-a
오브젝트 나열하는 중: 5, 완료.
오브젝트 개수 세는 중: 100% (5/5), 완료.
Delta compression using up to 24 threads
오브젝트 압축하는 중: 100% (3/3), 완료.
오브젝트 쓰는 중: 100% (3/3), 392 바이트 | 392.00 KiB/s, 완료.
Total 3 (delta 1), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (1/1), completed with 1 local object.
remote: 
remote: Create a pull request for 'branch-a' on GitHub by visiting:
remote:      https://github.com/SpartaPA/assignment1_jje/pull/new/branch-a
remote: 
To github.com:SpartaPA/assignment1_jje.git
 * [new branch]      branch-a -> branch-a
'branch-a' 브랜치가 리모트의 'branch-a' 브랜치를 ('origin'에서) 따라가도록 설정되었습니다.

```


**`branch-b`생성 및 README 수정**
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git switch -c branch-b
새로 만든 'branch-b' 브랜치로 전환합니다

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git add README.md 

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git commit -m "update:lidar 주기 20Hz로 수정"
[branch-b b15c32f] update:lidar 주기 20Hz로 수정
 1 file changed, 1 insertion(+), 1 deletion(-)
 
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git push -u origin branch-b
오브젝트 나열하는 중: 5, 완료.
오브젝트 개수 세는 중: 100% (5/5), 완료.
Delta compression using up to 24 threads
오브젝트 압축하는 중: 100% (3/3), 완료.
오브젝트 쓰는 중: 100% (3/3), 396 바이트 | 396.00 KiB/s, 완료.
Total 3 (delta 1), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (1/1), completed with 1 local object.
remote: 
remote: Create a pull request for 'branch-b' on GitHub by visiting:
remote:      https://github.com/SpartaPA/assignment1_jje/pull/new/branch-b
remote: 
To github.com:SpartaPA/assignment1_jje.git
 * [new branch]      branch-b -> branch-b
'branch-b' 브랜치가 리모트의 'branch-b' 브랜치를 ('origin'에서) 따라가도록 설정되었습니다.

```


**브랜치 병합 및 충돌 발생**
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git checkout main
'main' 브랜치로 전환합니다
브랜치가 'origin/main'에 맞게 업데이트된 상태입니다.

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git merge branch-a
업데이트 중 137ebc6..8e1a48e
Fast-forward
 README.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git merge branch-b
자동 병합: README.md
충돌 (내용): README.md에 병합 충돌
자동 병합이 실패했습니다. 충돌을 바로잡고 결과물을 커밋하십시오.

```
- 첫번째 병합에서는 정상적으로 병합되었으나, 두번째 병합에서 충돌이 났다는 터미널 출력이 발생됨

- 충돌 부분 ![conflict 발생](./images/conflict.png)
```text
<<<<<<< HEAD
| 2D 라이다  | 15Hz<br>(100ms) | 360점 × (거리 4B + 세기 4B) = 2,880B                           | 28.8 KB/s (≈ 0.23 Mbps)           | 장애물 감지                                     |
=======
| 2D 라이다  | 20Hz<br>(100ms) | 360점 × (거리 4B + 세기 4B) = 2,880B                           | 28.8 KB/s (≈ 0.23 Mbps)           | 장애물 감지                                     |
>>>>>>> branch-b
```
	
- `<<<<<<< HEAD` ~ `=======`: 현재 브랜치 (main, 이미 branch-a가 반영된 상태)의 내용
- `=======`: 두 내용의 경계선
- `=======` ~ `>>>>>>> branch-b`: 병합 시도 중인 branch-b의 내용

 
**충돌 해결**
- README.md 파일에서 충돌 난 부분 수정 - 10Hz로 통일
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git add README.md 

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git commit -m "merge: branch-b 충돌 해결 - 라이다 주기 10Hz로 통일"
[main aed2579] merge: branch-b 충돌 해결 - 라이다 주기 10Hz로 통일

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git push origin main
오브젝트 나열하는 중: 7, 완료.
오브젝트 개수 세는 중: 100% (7/7), 완료.
Delta compression using up to 24 threads
오브젝트 압축하는 중: 100% (3/3), 완료.
오브젝트 쓰는 중: 100% (3/3), 453 바이트 | 453.00 KiB/s, 완료.
Total 3 (delta 1), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (1/1), completed with 1 local object.
To github.com:SpartaPA/assignment1_jje.git
   137ebc6..aed2579  main -> main
```


---

### 3-4. Merge와 Rebase 이력 그래프

**rebase로 최신화**
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git checkout feature/compute-layout 
'feature/compute-layout' 브랜치로 전환합니다
브랜치가 'origin/feature/compute-layout'에 맞게 업데이트된 상태입니다.

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git rebase main

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git push --force-with-lease origin feature/compute-layout
오브젝트 나열하는 중: 4, 완료.
오브젝트 개수 세는 중: 100% (4/4), 완료.
Delta compression using up to 24 threads
오브젝트 압축하는 중: 100% (3/3), 완료.
오브젝트 쓰는 중: 100% (3/3), 2.26 KiB | 2.26 MiB/s, 완료.
Total 3 (delta 0), reused 0 (delta 0), pack-reused 0
To github.com:SpartaPA/assignment1_jje.git
 + adf80d2...1434f55 feature/compute-layout -> feature/compute-layout (forced update)
```
- `git rebase main`으로 rebase
- 원격에 강제 push

**main으로 병합**
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git checkout main
'main' 브랜치로 전환합니다
브랜치가 'origin/main'에 맞게 업데이트된 상태입니다.

pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git merge feature/compute-layout
업데이트 중 aed2579..1434f55
Fast-forward
 compute_layout.md | 18 ++++++++++++++++++
 1 file changed, 18 insertions(+)
 create mode 100644 compute_layout.md
```
- Fast-forward 병합: rebase로 이미 main 최신 커밋 뒤에 재배치되어 있었기 때문에, 별도 병합 커밋 없이 그대로 이어붙음


**이력 그래프 확인**
```bash
pa34@pa34-Legion-Pro-5-16IAX10:~/Desktop/physical_ai/projects/assignment1_jje$ git log --oneline --graph --all
* 1434f55 (HEAD -> main, origin/feature/compute-layout, feature/compute-layout) docs: 연산 분담 배치 설계 문서 추가
*   aed2579 (origin/main) merge: branch-b 충돌 해결 - 라이다 주기 10Hz로 통일
|\  
| * b15c32f (origin/branch-b, branch-b) update:lidar 주기 20Hz로 수정
* | 8e1a48e (origin/branch-a, branch-a) update:lidar 주기 15Hz로 수정
|/  
*   137ebc6 Merge pull request #2 from SpartaPA/feature/udev-rules
|\  
| * 628bd26 (origin/feature/udev-rules, feature/udev-rules) fix: 리뷰 반영 - 경로 변경 필요 주석 추가
| * 72488b5 feat: udev 규칙 파일 및 키 설명표 추가
|/  
* dd047c7 docs: 배달 로봇 센서 사양(센서 목록 및 주기) 작성
```
- merge 방식
	- 브랜치가 갈라졌다가 다시 합쳐지는 지접에 병합 커밋이 생겨, 그래프가 갈라지는 것과 합쳐지는 것을 확인 가능 (137ebc6, aed2579)
-  rebase 방식
	- 병합 커밋 없이 main 뒤에 커밋이 그대로 붙어 갈라지는 표시 없이 선형 구조로 붙어있음 (1434f55)


---

### 3-5. Merge와 Rebase를 언제 쓸지

- 공유 브랜치(main)에 기능을 합칠 때는 이력 보존과 협업 기록이 중요하므로 merge(PR 병합)를 사용
- 내 로컬 브랜치를 최신 main과 동기화할 때는 지저분한 병합 커밋 없이 깔끔한 이력을 위해 rebase를 사용
- 단, 이미 push되어 다른 사람이 봤을 수 있는 공유 커밋은 팀 저장소 히스토리가 꼬이므로 절대 rebase 사용하지 X


---
#### 참고 자료


[^1]: systemd `udevadm-info.c`의 `print_all_attributes()` 함수는 `if (value[0] == '/') continue;` 로직으로 경로 형태의 속성값을 건너뛴다. (https://github.com/systemd/systemd/blob/main/src/udev/udevadm-info.c)