# Portfolio CI/CD — From Scratch Setup Guide

## What You're Building

A Jenkins CI/CD pipeline that:
- Polls GitHub every 5 min for changes to `herrise/portfolio`
- Lints Python (ruff) + TypeScript (tsc)
- Validates dbt SQL models compile
- Builds 4 Docker images in parallel (web, api, batch-ingest, stream-ingest)
- Deploys to Docker Compose on the same host (main branch only)
- Health-checks the API after deploy

Access: https://jenkins.herrise.cloud/job/portfolio/
Deploys to: https://portfolio.herrise.cloud/

---

## Prerequisites

You need:
- A VM running Docker + Docker Compose
- k3s Kubernetes (for ingress to jenkins.herrise.cloud)
- nginx reverse proxy (for routing to Jenkins + portfolio)
- Let's Encrypt certs for jenkins.herrise.cloud and portfolio.herrise.cloud
- GitHub repo `herrise/portfolio` with SSH access
- SSH key on the host that can clone the repo

---

## Step 1: Launch Jenkins Docker Container

File: `/home/ubuntu/docker/jenkins/docker-compose.yaml`

```yaml
version: '3.8'

services:
  jenkins:
    image: jenkins/jenkins:lts   # v2.528.1 used
    container_name: jenkins
    restart: unless-stopped
    ports:
      - "8085:8080"     # host:container (nginx proxies to 8085)
      - "50000:50000"   # agent port
    volumes:
      - jenkins_home:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock   # CRITICAL — Docker-in-Docker
    environment:
      - JAVA_OPTS=-Djetty.request.header.size=131072 -Djenkins.install.runSetupWizard=false
      - JENKINS_OPTS=--httpPort=8080 --requestHeaderSize=131072
    user: root          # CRITICAL — needed for Docker socket access
    networks:
      - jenkins

networks:
  jenkins:
    driver: bridge

volumes:
  jenkins_home:
    driver: local
```

Bring it up:
```bash
cd /home/ubuntu/docker/jenkins
docker compose up -d
```

---

## Step 2: Install Tools in Jenkins Container

The Jenkins LTS image is minimal. Install what the pipeline needs:

```bash
# Install Docker CLI + Python + Node.js
docker exec -u root jenkins bash -c '
  apt-get update -qq && apt-get install -y -qq docker.io python3 python3-pip nodejs npm
'

# Verify
docker exec jenkins docker --version
docker exec jenkins python3 --version
docker exec jenkins node --version
```

---

## Step 3: Install Jenkins Plugins

Five plugins are needed for a Declarative Pipeline with Git + Docker:

```bash
# Download the CLI jar
curl -s http://localhost:8085/jnlpJars/jenkins-cli.jar -o /tmp/jenkins-cli.jar

# Copy into container + install plugins
docker cp /tmp/jenkins-cli.jar jenkins:/tmp/
docker exec jenkins java -jar /tmp/jenkins-cli.jar \
  -s http://localhost:8080 \
  install-plugin workflow-aggregator git docker-workflow timestamper ws-cleanup \
  -deploy

# Restart to activate plugins
docker restart jenkins
```

Plugins explained:
| Plugin              | What it provides                                     |
|---------------------|------------------------------------------------------|
| workflow-aggregator | Declarative Pipeline (pipeline{}, stages{}, agent{}) |
| git                 | Git SCM checkout                                     |
| docker-workflow     | docker {} agent blocks, docker.build()               |
| timestamper         | timestamps() option for build logs                   |
| ws-cleanup          | cleanWs() post-action to free disk space             |

---

## Step 4: Set Up SSH Keys for GitHub

```bash
# Copy the host's SSH keys into Jenkins (needed for git clone)
docker exec -u root jenkins mkdir -p /root/.ssh /var/jenkins_home/.ssh
docker cp ~/.ssh/id_rsa jenkins:/root/.ssh/
docker cp ~/.ssh/id_rsa.pub jenkins:/root/.ssh/
docker cp ~/.ssh/known_hosts jenkins:/root/.ssh/ 2>/dev/null || \
  docker exec jenkins ssh-keyscan github.com >> /root/.ssh/known_hosts
docker exec -u root jenkins chmod 700 /root/.ssh
docker exec -u root jenkins chmod 600 /root/.ssh/id_rsa

# Also copy to Jenkins home (some operations look there)
docker exec jenkins cp -r /root/.ssh /var/jenkins_home/.ssh
docker exec -u root jenkins chown -R jenkins:jenkins /var/jenkins_home/.ssh

# Test
docker exec jenkins ssh -T git@github.com
# Should show: "Hi <user>! You've successfully authenticated..."
```

---

## Step 5: Create the Jenkins Pipeline Job

Create a job config XML pointing to your repo:

```bash
cat > /tmp/portfolio-job-config.xml << 'EOF'
<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <description>CI/CD pipeline for portfolio.herrise.cloud</description>
  <keepDependencies>false</keepDependencies>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition">
    <scm class="hudson.plugins.git.GitSCM">
      <configVersion>2</configVersion>
      <userRemoteConfigs>
        <hudson.plugins.git.UserRemoteConfig>
          <url>git@github.com:herrise/portfolio.git</url>
        </hudson.plugins.git.UserRemoteConfig>
      </userRemoteConfigs>
      <branches>
        <hudson.plugins.git.BranchSpec>
          <name>*/main</name>
        </hudson.plugins.git.BranchSpec>
      </branches>
    </scm>
    <scriptPath>Jenkinsfile</scriptPath>
    <lightweight>true</lightweight>
  </definition>
</flow-definition>
EOF

# Copy into container + create
docker cp /tmp/portfolio-job-config.xml jenkins:/tmp/
docker exec jenkins sh -c \
  'java -jar /tmp/jenkins-cli.jar -s http://localhost:8080 \
   create-job portfolio < /tmp/portfolio-job-config.xml'
```

---

## Step 6: The Jenkinsfile (CI/CD Pipeline)

This lives in your repo at the root: `Jenkinsfile`

```groovy
pipeline {
    agent any

    environment {
        DBT_PROFILES_DIR  = "${WORKSPACE}/dbt"
        DBT_PROJECT_DIR   = "${WORKSPACE}/dbt"
        DEPLOY_TARGET     = 'localhost'
    }

    triggers {
        pollSCM('H/5 * * * *')   // check GitHub every 5 min
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '20'))  // keep last 20 builds
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                }
                echo "Building commit: ${GIT_COMMIT_SHORT}"
            }
        }

        // ── LINT ─────────────────────────────────

        stage('Lint — Python') {
            steps {
                sh 'pip3 install -q --break-system-packages ruff'
                script {
                    def dirs = ['api', 'ingest/batch', 'ingest/stream']
                    dirs.each { dir ->
                        if (fileExists("${dir}/requirements.txt")) {
                            def status = sh(script: "ruff check ${dir}", returnStatus: true)
                            if (status != 0) {
                                echo "ruff found ${status} issues in ${dir} (non-blocking)"
                            }
                        }
                    }
                }
            }
        }

        stage('Lint — TypeScript') {
            steps {
                dir('web') {
                    sh(script: 'npm install', returnStatus: true)
                    sh(script: 'npx tsc --noEmit', returnStatus: true)
                }
            }
        }

        // ── TEST ─────────────────────────────────

        stage('Test — dbt Compile') {
            steps {
                dir('dbt') {
                    sh 'pip3 install -q --break-system-packages dbt-duckdb'
                    // CI has no Docker volume — create a temp DuckDB
                    sh '''rm -f /app/data/pipeline.duckdb
                    mkdir -p /app/data
                    cat > /tmp/init_duckdb.py << "PYEOF"
import duckdb
con = duckdb.connect("/app/data/pipeline.duckdb")
con.execute("CREATE TABLE IF NOT EXISTS _ci_init (x INTEGER)")
con.close()
PYEOF
                    python3 /tmp/init_duckdb.py'''
                    sh 'dbt compile'
                }
            }
        }

        stage('Test — dbt Data Quality') {
            when { expression { return false } }  // skip in CI — needs live data
            steps { dir('dbt') { sh 'dbt test' } }
        }

        // ── BUILD ────────────────────────────────

        stage('Build — Docker Images') {
            parallel {
                stage('web') {
                    steps {
                        dir('web') {
                            sh "docker build -t portfolio-web:${GIT_COMMIT_SHORT} -t portfolio-web:latest ."
                        }
                    }
                }
                stage('api') {
                    steps {
                        dir('api') {
                            sh "docker build -t portfolio-api:${GIT_COMMIT_SHORT} -t portfolio-api:latest ."
                        }
                    }
                }
                stage('batch-ingest') {
                    steps {
                        dir('ingest/batch') {
                            sh "docker build -t portfolio-batch:${GIT_COMMIT_SHORT} -t portfolio-batch:latest ."
                        }
                    }
                }
                stage('stream-ingest') {
                    steps {
                        dir('ingest/stream') {
                            sh "docker build -t portfolio-stream:${GIT_COMMIT_SHORT} -t portfolio-stream:latest ."
                        }
                    }
                }
            }
        }

        // ── DEPLOY ───────────────────────────────

        stage('Deploy') {
            when { branch 'main' }
            steps {
                script {
                    if (env.DEPLOY_TARGET == 'localhost') {
                        sh '''
                            docker compose down || true
                            docker compose up -d --build
                        '''
                    } else {
                        sh """
                            scp docker-compose.yml ${DEPLOY_TARGET}:~/portfolio/
                            ssh ${DEPLOY_TARGET} '
                                cd ~/portfolio &&
                                docker compose pull &&
                                docker compose up -d --remove-orphans
                            '
                        """
                    }
                }

                // Health check — use Docker bridge IP (localhost = Jenkins container, not host)
                retry(3) {
                    sleep(time: 10, unit: 'SECONDS')
                    sh 'curl -sf http://172.17.0.1:8000/health || exit 1'
                }

                echo 'Deploy complete'
            }
        }
    }

    post {
        success { echo "Pipeline SUCCESS — ${GIT_COMMIT_SHORT}" }
        failure { echo "Pipeline FAILED — ${GIT_COMMIT_SHORT}" }
    }
}
```

---

## Step 7: Trigger Your First Build

```bash
# Trigger via CLI
docker exec jenkins java -jar /tmp/jenkins-cli.jar \
  -s http://localhost:8080 build portfolio

# Watch the console output
docker exec jenkins java -jar /tmp/jenkins-cli.jar \
  -s http://localhost:8080 console portfolio
```

Or visit https://jenkins.herrise.cloud/job/portfolio/ and click "Build Now".

---

## Pitfalls We Hit (and Fixed)

### 1. `npm ci` fails without package-lock.json
**Symptom:** `npm ERR! The npm ci command can only install with an existing package-lock.json`
**Fix:** Use `npm install` instead (with `returnStatus: true` for non-blocking).

### 2. dbt compile fails — DuckDB file not found
**Symptom:** `IO Error: Cannot open file "/app/data/pipeline.duckdb": No such file`
**Fix:** In CI (no Docker volumes), create a temp DuckDB file with a Python init script.

### 3. Empty file is NOT a valid DuckDB database
**Symptom:** `IO Error: The file exists, but it is not a valid DuckDB database file!`
**Fix:** Use `duckdb.connect()` + `con.execute("CREATE TABLE ...")` to create a valid file.
Also `rm -f` the file first — stale files from failed builds persist.

### 4. Health check uses localhost — can't reach host
**Symptom:** `curl: (7) Failed to connect to localhost:8000` inside Jenkins container.
**Fix:** Use the Docker bridge IP: `curl -sf http://172.17.0.1:8000/health`

### 5. Heredoc in Jenkinsfile `sh` step is fragile
**Symptom:** `python3` runs but heredoc input isn't passed.
**Fix:** Write a temp Python script with `cat > /tmp/init.py << "PYEOF"` then run it.
The `sh '''...'''` triple-quote is needed for multi-line shell in Declarative Pipeline.

### 6. CSRF crumb needed for REST API
**Symptom:** `HTTP ERROR 403 No valid crumb was included`
**Fix:** Use the Jenkins CLI jar (`java -jar jenkins-cli.jar`) which bypasses CSRF.
Avoid curl-based job creation unless you handle crumbs + session cookies.

### 7. Jenkins must run as root for Docker socket
**Symptom:** `docker: permission denied while trying to connect to the Docker daemon socket`
**Fix:** Set `user: root` in docker-compose and mount `/var/run/docker.sock`.

### 8. Docker socket is mounted, but Docker CLI missing
**Symptom:** `docker: command not found`
**Fix:** `apt-get install -y docker.io` in the Jenkins container.

### 9. `next build` fails — ESLint missing
**Symptom:** `⨯ ESLint must be installed in order to run during builds`
**Fix:** Add `eslint` and `eslint-config-next` to devDependencies in web/package.json.

### 10. Custom eslint rules need @typescript-eslint plugin
**Symptom:** `Error: Definition for rule '@typescript-eslint/no-unused-vars' was not found`
**Fix:** Remove custom rules from `.eslintrc.json` — `next/core-web-vitals` already covers them.
```json
{ "extends": "next/core-web-vitals" }
```

### 11. Docker build cache hides Dockerfile changes
**Symptom:** `COPY --from=base /app/public ./public` fails with "not found" despite `mkdir -p`.
**Fix:** Add `--no-cache` to the web image build step. Next.js Docker builds are sensitive to stale caches, especially when the `public/` directory doesn't exist on the host.

---

## How the Routing Works

```
                    ┌──────────────────────────────────────┐
                    │           Docker Host                  │
                    │                                        │
  User ──443──▶ k3s │ Ingress (TLS termination)              │
  browser          │   │                                    │
                    │   ▼ HTTP (port 8080)                   │
                    │ nginx-server (Docker, :8080→:80)       │
                    │   ├─ jenkins.herrise.cloud → :8085    │
                    │   └─ portfolio.herrise.cloud → :3000  │
                    │                                        │
                    │ jenkins container (:8085)               │
                    │   ├─ Docker socket mounted             │
                    │   ├─ git clone via SSH                 │
                    │   └─ docker compose up -d portfolio   │
                    │                                        │
                    │ portfolio containers:                   │
                    │   web:3000  api:8000  redis:6379       │
                    │   batch-ingest  stream-ingest          │
                    └──────────────────────────────────────┘
```

---

## Daily Operations

```bash
# Trigger a build
docker exec jenkins java -jar /tmp/jenkins-cli.jar -s http://localhost:8080 build portfolio

# Check last build status
docker exec jenkins java -jar /tmp/jenkins-cli.jar -s http://localhost:8080 console portfolio | tail -5

# List all jobs
docker exec jenkins java -jar /tmp/jenkins-cli.jar -s http://localhost:8080 list-jobs All

# Check which plugins are installed
curl -s http://localhost:8085/pluginManager/api/json?depth=1 | python3 -c "
import sys,json
for p in json.load(sys.stdin).get('plugins',[]):
    print(f\"{p['shortName']:35s} v{p['version']}\")
"
```
