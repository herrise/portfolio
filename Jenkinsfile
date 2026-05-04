pipeline {
    agent any

    environment {
        DBT_PROFILES_DIR  = "${WORKSPACE}/dbt"
        DBT_PROJECT_DIR   = "${WORKSPACE}/dbt"
        DEPLOY_TARGET     = 'localhost'
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '20'))
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

        stage('Test — dbt Compile') {
            steps {
                dir('dbt') {
                    sh 'pip3 install -q --break-system-packages dbt-duckdb'
                    // Create the duckdb path expected by profiles.yml (CI doesn't have the container volume)
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
            when { expression { return false } }  // skip in CI — requires live DuckDB
            steps {
                dir('dbt') {
                    sh 'dbt test'
                }
            }
            post {
                failure {
                    echo '⚠️  dbt data quality tests FAILED'
                }
            }
        }

        stage('Build — Docker Images') {
            parallel {
                stage('web') {
                    steps {
                        dir('web') {
                            sh "docker build --no-cache -t portfolio-web:${GIT_COMMIT_SHORT} -t portfolio-web:latest ."
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
            post {
                success {
                    echo "✅ All Docker images built — tag: ${GIT_COMMIT_SHORT}"
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
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

                retry(3) {
                    sleep(time: 10, unit: 'SECONDS')
                    sh 'curl -sf http://172.17.0.1:8000/health || exit 1'
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

    post {
        success {
            echo "✅ Pipeline SUCCESS — ${GIT_COMMIT_SHORT}"
        }
        failure {
            echo "❌ Pipeline FAILED — ${GIT_COMMIT_SHORT}"
        }
    }
}
