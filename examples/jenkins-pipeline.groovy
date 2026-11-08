pipeline {
    agent any
    
    environment {
        PIP_CACHE_DIR = '.cache/pip'
    }
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }
    
    stages {
        stage('Lint') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-v $HOME/.cache/pip:/root/.cache/pip'
                }
            }
            steps {
                sh 'pip install -e ".[dev]"'
                sh 'ruff check src tests'
                sh 'ruff format --check src tests'
            }
        }
        
        stage('Test') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-v $HOME/.cache/pip:/root/.cache/pip'
                }
            }
            parallel {
                stage('Python 3.11') {
                    steps {
                        sh 'pytest --cov=pipeline_doctor --cov-report=xml --cov-report=term-missing'
                    }
                }
                stage('Python 3.12') {
                    agent {
                        docker {
                            image 'python:3.12-slim'
                            args '-v $HOME/.cache/pip:/root/.cache/pip'
                        }
                    }
                    steps {
                        sh 'pytest --cov=pipeline_doctor'
                    }
                }
            }
        }
        
        stage('Build') {
            agent {
                docker {
                    image 'python:3.11-slim'
                    args '-v $HOME/.cache/pip:/root/.cache/pip'
                }
            }
            when {
                branch 'main'
            }
            steps {
                sh 'pip install build twine'
                sh 'python -m build'
                sh 'twine check dist/*'
            }
            post {
                success {
                    archiveArtifacts artifacts: 'dist/*', fingerprint: true
                }
            }
        }
        
        stage('Docker') {
            agent {
                docker {
                    image 'docker:24-dind'
                    args '-v /var/run/docker.sock:/var/run/docker.sock'
                }
            }
            when {
                branch 'main'
            }
            steps {
                script {
                    docker.withRegistry('https://registry.example.com', 'registry-credentials') {
                        def image = docker.build("pipeline-doctor:${BUILD_NUMBER}")
                        image.push()
                        image.push('latest')
                    }
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        failure {
            emailext (
                subject: "Build Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: "Build failed. Check console output at ${env.BUILD_URL}",
                to: '${DEFAULT_RECIPIENTS}'
            )
        }
    }
}