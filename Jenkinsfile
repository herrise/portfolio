pipeline {
    agent any

    // ── Global environment ──────────────────────────────────────────
    environment {
        // Don't prompt for input in automated runs
        DBT_PROFILES_DIR      = "${WORKSPACE}/dbt"
        DBT_PROJECT_DIR       = "${WORKSPACE}/dbt"
        DOCKER_REGISTRY       = ''                  // e.g. 'your-registry.com/portfolio'
        DEPLOY_TARGET         = 'localhost'         // SSH host or '' for local deploy
        SLACK_CHANNEL         = '#ci-cd'            // optional
    }

    // ── Triggers ────────────────────────────────────────────────────
    triggers {
        // Poll SCM every 5 minutes (adjust as needed)
        pollSCM('H/5 * * * *')
    }

    // ── Options ─────────────────────────────────────────────────────
    options {
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '5'))
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    // ── Stages ──────────────────────────────────────────────────────
    stages {

        // ============================================================
        stage('Checkout') {
            steps {
                checkout scm

                script {
                    // Capture short commit SHA for tagging
                    env.GIT_COMMIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                }

                echo "Building commit: ${GIT_COMMIT_SHORT}"
            }
        }

        // ============================================================
        stage('Lint — Python') {
            agent {
                docker {
                    image 'python:3.12-slim'
                    reuseNode true
                }
            }
            steps {
                script {
                    dirs = ['api', 'ingest/batch', 'ingest/stream']
                    dirs.each { dir ->
                        if (fileExists("${dir}/requirements.txt")) {
                            sh """
                                pip install -q ruff
                                ruff check ${dir}/
                            """
                        }
                    }
                }
            }
        }

        // ============================================================
        stage('Lint — TypeScript') {
            agent {
                docker {
                    image 'node:20-alpine'
                    reuseNode true
                }
            }
            steps {
                dir('web') {
                    sh 'npm ci'
                    sh 'npx tsc --noEmit'
                    // Optional: ESLint if configured
                    // sh 'npx next lint'
                }
            }
        }

        // ============================================================
        stage('dbt — Compile') {
            agent {
                docker {
                    image 'ghcr.io/dbt-labs/dbt-duckdb:1.7.0'
                    reuseNode true
                }
            }
            steps {
                dir('dbt') {
                    sh 'dbt compile'
                }
            }
            post {
                failure {
                    echo 'dbt compile failed — models may have syntax errors'
                }
            }
        }

        // ============================================================
        stage('dbt — Test') {
            agent {
                docker {
                    image 'ghcr.io/dbt-labs/dbt-duckdb:1.7.0'
                    reuseNode true
                }
            }
            steps {
                dir('dbt') {
                    // Run dbt tests (not_null, unique on star schema)
                    sh 'dbt test'
                }
            }
            post {
                failure {
                    echo '⚠️  dbt data quality tests FAILED'
                    // slackSend(channel: SLACK_CHANNEL, color: 'danger',
                    //           message: "dbt tests failed on ${GIT_COMMIT_SHORT}")
                }
            }
        }

        // ============================================================
        stage('Build — Docker Images') {
            parallel {
                stage('web') {
                    steps {
                        dir('web') {
                            sh """
                                docker build \
                                    -t portfolio-web:${GIT_COMMIT_SHORT} \
                                    -t portfolio-web:latest \
                                    .
                            """
                        }
                    }
                }
                stage('api') {
                    steps {
                        dir('api') {
                            sh """
                                docker build \
                                    -t portfolio-api:${GIT_COMMIT_SHORT} \
                                    -t portfolio-api:latest \
                                    .
                            """
                        }
                    }
                }
                stage('batch-ingest') {
                    steps {
                        dir('ingest/batch') {
                            sh """
                                docker build \
                                    -t portfolio-batch:${GIT_COMMIT_SHORT} \
                                    -t portfolio-batch:latest \
                                    .
                            """
                        }
                    }
                }
                stage('stream-ingest') {
                    steps {
                        dir('ingest/stream') {
                            sh """
                                docker build \
                                    -t portfolio-stream:${GIT_COMMIT_SHORT} \
                                    -t portfolio-stream:latest \
                                    .
                            """
                        }
                    }
                }
            }
            post {
                success {
                    echo "✅ All Docker images built — tag: ${GIT_COMMIT_SHORT}"
                }
            }
        }

        // ============================================================
        stage('Deploy') {
            when {
                // Only deploy from main branch
                branch 'main'
            }
            steps {
                script {
                    if (env.DEPLOY_TARGET == 'localhost') {
                        // Local Docker Compose deploy
                        sh '''
                            cd ${WORKSPACE}
                            docker compose down
                            docker compose up -d --build
                        '''
                    } else {
                        // Remote deploy via SSH
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

                // Health check — wait for API to respond
                retry(3) {
                    sleep(time: 10, unit: 'SECONDS')
                    sh 'curl -sf http://localhost:8000/health || exit 1'
                }

                echo '🚀 Deploy complete'
            }
            post {
                failure {
                    echo '❌ Deploy failed — check logs'
                }
                success {
                    echo "✅ Deploy succeeded — http://localhost:3000"
                }
            }
        }
    }

    // ── Post-build actions ──────────────────────────────────────────
    post {
        success {
            echo "✅ Pipeline SUCCESS — ${GIT_COMMIT_SHORT}"
        }
        failure {
            echo "❌ Pipeline FAILED — check Jenkins console"
        }
        always {
            cleanWs(
                cleanWhenNotBuilt: false,
                deleteDirs: true,
                disableDeferredWipeout: false
            )
        }
    }
}
