{% macro generate_sk(column_name) %}
    CAST(MD5(CAST({{ column_name }} AS VARCHAR)) AS VARCHAR)
{% endmacro %}
